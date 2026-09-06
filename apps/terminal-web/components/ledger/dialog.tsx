"use client";
import { useEffect, useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";
import { IconButton } from "../ui";

export function LedgerDialog({
  title,
  children,
  onClose,
  closeLabel = "Close accounting dialog",
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  closeLabel?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const heading = useId();
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const opener = document.activeElement;
    element.showModal();
    return () => {
      element.close();
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className="ledger-dialog"
      aria-labelledby={heading}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <header className="ledger-dialog-header">
        <h2 id={heading}>{title}</h2>
        <IconButton label={closeLabel} onClick={onClose}>
          <X size={15} />
        </IconButton>
      </header>
      <div className="ledger-dialog-content">{children}</div>
    </dialog>
  );
}

export function LedgerError({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <div role="alert" className="ledger-error">
      {error instanceof Error ? error.message : "The accounting request failed"}
    </div>
  );
}

export function LedgerLoading() {
  return (
    <div role="status" className="ledger-loading">
      Loading ledger...
    </div>
  );
}
