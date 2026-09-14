/** Who makes the site, and where its code is, as one line. */
export default function MadeBy({ className = "" }: { className?: string }) {
  return (
    <p className={`label ${className}`}>
      A{" "}
      <a href="https://filtercoffee.dev" className="ink-link font-semibold">
        filtercoffee.dev
      </a>{" "}
      project, open source{" "}
      <a href="https://github.com/sagrkv/LakesOfBendakaluru" className="ink-link font-semibold">
        on GitHub
      </a>
    </p>
  );
}
