interface Column<T> {
  key: keyof T | string;
  label: string;
  fmt?: (v: unknown, row: T) => string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  emptyText?: string;
}

export default function DataTable<T extends object>({
  columns,
  rows,
  emptyText = "Nenhum registro.",
}: DataTableProps<T>) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={String(c.key)}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="py-8 text-center text-sm text-ink-muted-48">
                {emptyText}
              </td>
            </tr>
          ) : (
            rows.map((row, i) => (
              <tr key={i}>
                {columns.map((c) => {
                  const r = row as Record<string, unknown>;
                  let v: unknown = r[c.key as string];
                  if (c.fmt) v = c.fmt(v, row);
                  else if (v === null || v === undefined) v = "—";
                  else if (typeof v === "boolean") v = v ? "Sim" : "Não";
                  return (
                    <td key={String(c.key)} className="text-ink">
                      {String(v)}
                    </td>
                  );
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
