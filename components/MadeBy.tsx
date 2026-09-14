/** Who makes the site, as one line. */
export default function MadeBy({ className = "" }: { className?: string }) {
  return (
    <p className={`label ${className}`}>
      A{" "}
      <a href="https://filtercoffee.dev" className="ink-link font-semibold">
        filtercoffee.dev
      </a>{" "}
      project
    </p>
  );
}
