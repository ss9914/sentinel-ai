export default function Badge({ value }) {
  return <span className={`badge badge-${String(value).toLowerCase()}`}>{value}</span>;
}
