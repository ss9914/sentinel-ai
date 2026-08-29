import Badge from "./Badge";

export default function Table({ title, columns, rows, empty = "No records yet." }) {
  return <section className="panel"><h2>{title}</h2>{rows.length ? <div className="table-wrap"><table><thead><tr>{columns.map((col) => <th key={col.label}>{col.label}</th>)}</tr></thead><tbody>{rows.map((row) => <tr key={row.id}>{columns.map((col) => <td key={col.label}>{col.badge ? <Badge value={row[col.key]} /> : col.render ? col.render(row) : row[col.key]}</td>)}</tr>)}</tbody></table></div> : <p className="empty">{empty}</p>}</section>;
}
