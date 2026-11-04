export function Notice({ message }: { message: string }) {
  if (!message) return null;
  return <div className="notice" role="alert">{message}</div>;
}
