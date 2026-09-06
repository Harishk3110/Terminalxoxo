import { execFileSync, spawn, type ChildProcess } from "node:child_process";
import { mkdirSync, openSync, closeSync } from "node:fs";
import { randomBytes } from "node:crypto";
import { request } from "@playwright/test";
import http from "node:http";
import path from "node:path";

function reachable(url: string) {
  return new Promise<boolean>(resolve => {
    const request=http.get(url,response=>{response.resume();resolve(response.statusCode===200);});
    request.setTimeout(1500,()=>{request.destroy();resolve(false);});
    request.on('error',()=>resolve(false));
  });
}

export default async function setup() {
  const root=process.cwd();
  const id=process.env.PLAYWRIGHT_RUN_ID || String(Date.now());
  mkdirSync('logs',{recursive:true});
  const children:ChildProcess[]=[];
  const stop=async()=>{
    for(const child of children.reverse()) {
      if(!child.pid) continue;
      try {
        if(process.platform==='win32') execFileSync('taskkill',['/PID',String(child.pid),'/T','/F'],{stdio:'ignore',windowsHide:true,timeout:15000});
        else child.kill('SIGTERM');
      } catch { child.kill(); }
    }
  };
  const start=(binary:string,args:string[],cwd:string,env:NodeJS.ProcessEnv,name:string)=>{
    const log=openSync(path.join(root,`logs/e2e-${id}-${name}.log`),'a');
    const child=spawn(binary,args,{cwd,env:{...process.env,...env},windowsHide:true,stdio:['ignore',log,log]});
    closeSync(log);
    child.on('error',()=>{});
    children.push(child);
  };
  try {
    for(const url of ['http://127.0.0.1:8001/health/live','http://127.0.0.1:3002/login']) {
      if(await reachable(url)) throw new Error(`Test port is already occupied: ${url}`);
    }
    start(process.env.PLAYWRIGHT_PYTHON || (process.platform==='win32'?'python':'python3'),['-m','uvicorn','app.main:app','--app-dir','services/api','--host','127.0.0.1','--port','8001'],root,{
      DATABASE_URL:`sqlite:///${path.join(root,`logs/e2e-${id}.db`).replaceAll('\\','/')}`,
      OBJECT_STORAGE_LOCAL_DIR:path.join(root,`logs/e2e-objects-${id}`),KNK_ENV:'local-demo',
    },'api');
    start(process.execPath,[path.join(root,'apps/terminal-web/node_modules/next/dist/bin/next'),'start','--hostname','127.0.0.1','--port','3002'],path.join(root,'apps/terminal-web'),{
      KNK_NEXT_DIST_DIR:process.env.PLAYWRIGHT_DIST_DIR || '.next',KNK_API_URL:'http://127.0.0.1:8001',NEXT_PUBLIC_APP_ENV:'test',
    },'web');
    for(const url of ['http://127.0.0.1:8001/health/live','http://127.0.0.1:3002/login']) {
      const deadline=Date.now()+240000;
      while(!(await reachable(url))) {
        if(Date.now()>deadline || children.some(c=>c.exitCode!==null)) throw new Error(`Test service failed: ${url}; inspect logs/e2e-${id}-*.log`);
        await new Promise(resolve=>setTimeout(resolve,500));
      }
    }
    const email = 'browser-' + id + '@example.test';
    const password = randomBytes(24).toString('base64url');
    process.env.PLAYWRIGHT_TEST_EMAIL = email;
    process.env.PLAYWRIGHT_TEST_PASSWORD = password;
    const api = await request.newContext({ baseURL: 'http://127.0.0.1:3002' });
    const configured = await api.post('/backend/api/v1/auth/setup', { data: { email, password } });
    if (!configured.ok()) throw new Error('Isolated test administrator provisioning failed');
    const loggedIn = await api.post('/backend/api/v1/auth/login', { data: { email, password } });
    if (!loggedIn.ok()) throw new Error('Isolated test sign-in failed');
    await api.storageState({ path: 'logs/e2e-auth.json' });
    await api.dispose();
    return stop;
  } catch(error) { await stop(); throw error; }
}
