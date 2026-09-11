import net from "node:net";

export function portOccupied(port: number): Promise<boolean> {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", (error: NodeJS.ErrnoException) => {
      if (error.code === "EADDRINUSE") resolve(true);
      else reject(error);
    });
    server.listen({ port, host: "127.0.0.1", exclusive: true }, () => {
      server.close(error => error ? reject(error) : resolve(false));
    });
  });
}
