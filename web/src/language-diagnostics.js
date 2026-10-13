/** LSP input is external data. Keep only valid ordered UTF-16 ranges. */
export function validDiagnostics(value){
  if(!Array.isArray(value))return [];
  const position=p=>p&&Number.isInteger(p.line)&&p.line>=0&&Number.isInteger(p.character)&&p.character>=0;
  return value.slice(0,500).filter(d=>d&&position(d.range?.start)&&position(d.range?.end)&&(d.range.end.line>d.range.start.line||d.range.end.line===d.range.start.line&&d.range.end.character>=d.range.start.character));
}
