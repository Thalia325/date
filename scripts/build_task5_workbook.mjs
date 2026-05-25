import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const repoRoot = process.cwd();
const csvPath = path.join(repoRoot, "data", "processed", "task5_dataset_review.csv");
const schemaPath = path.join(repoRoot, "data", "processed", "task5_graph_schema.json");
const outputDir = path.join(repoRoot, "outputs", "task5");
const outputPath = path.join(outputDir, "task5_dataset_review.xlsx");

function parseCsv(text) {
  const rows = [];
  let row = [];
  let value = "";
  let inQuotes = false;
  const clean = text.replace(/^\uFEFF/, "");

  for (let i = 0; i < clean.length; i += 1) {
    const ch = clean[i];
    const next = clean[i + 1];
    if (inQuotes) {
      if (ch === '"' && next === '"') {
        value += '"';
        i += 1;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        value += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      row.push(value);
      value = "";
    } else if (ch === "\n") {
      row.push(value.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      value = "";
    } else {
      value += ch;
    }
  }
  if (value.length > 0 || row.length > 0) {
    row.push(value.replace(/\r$/, ""));
    rows.push(row);
  }
  return rows.filter((item) => item.some((cell) => cell !== ""));
}

function rowsToObjects(rows) {
  const [headers, ...data] = rows;
  return data.map((row) => Object.fromEntries(headers.map((header, i) => [header, row[i] ?? ""])));
}

function countBy(items, key) {
  const counts = new Map();
  for (const item of items) {
    counts.set(item[key], (counts.get(item[key]) ?? 0) + 1);
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1]);
}

function truncate(text, max = 110) {
  if (!text) return "";
  return text.length > max ? `${text.slice(0, max - 1)}...` : text;
}

const csvText = await fs.readFile(csvPath, "utf8");
const csvRows = parseCsv(csvText);
const records = rowsToObjects(csvRows);
const schema = JSON.parse(await fs.readFile(schemaPath, "utf8"));

const workbook = Workbook.create();
const summary = workbook.worksheets.add("Summary");
const review = workbook.worksheets.add("Dataset Review");
const schemaSheet = workbook.worksheets.add("Graph Schema");
const sources = workbook.worksheets.add("Sources");

for (const sheet of [summary, review, schemaSheet, sources]) {
  sheet.showGridLines = false;
}

summary.getRange("A1:H1").merge();
summary.getRange("A1").values = [["Task 5 Dataset Cleaning Review"]];
summary.getRange("A1").format = {
  fill: "#17324D",
  font: { color: "#FFFFFF", bold: true, size: 16 },
  horizontalAlignment: "left",
};

summary.getRange("A3:B8").values = [
  ["Audit date", "2026-05-25"],
  ["Candidate sources reviewed", records.length],
  ["Core datasets", records.filter((r) => r.cleaned_use_tier === "core").length],
  ["Auxiliary datasets", records.filter((r) => r.cleaned_use_tier === "auxiliary").length],
  ["Transfer-only datasets", records.filter((r) => r.cleaned_use_tier === "transfer_only").length],
  ["Local raw roots present", records.filter((r) => r.local_status === "present").length],
];
summary.getRange("A3:A8").format = { fill: "#EAF2F8", font: { bold: true } };
summary.getRange("B3:B8").format = { horizontalAlignment: "left" };

const decisionCounts = countBy(records, "cleaned_use_tier");
summary.getRange("D3:E3").values = [["Cleaned tier", "Count"]];
summary.getRange(`D4:E${3 + decisionCounts.length}`).values = decisionCounts;
summary.getRange(`D3:E${3 + decisionCounts.length}`).format = { wrapText: true };
summary.getRange("D3:E3").format = { fill: "#2F6F73", font: { color: "#FFFFFF", bold: true } };

summary.getRange("A11:H11").merge();
summary.getRange("A11").values = [["Recommended execution path"]];
summary.getRange("A11").format = { fill: "#17324D", font: { color: "#FFFFFF", bold: true } };
summary.getRange("A12:H16").values = [
  ["1", "RxnScribe", "Build reaction scheme graph baseline: reactants/products as nodes, arrows as edges, condition text as parameters.", "", "", "", "", ""],
  ["2", "ReactionDataExtractor2", "Use as parser baseline and machine-readable graph output reference.", "", "", "", "", ""],
  ["3", "AI2D", "Use only for generic diagram node-arrow-text transfer, with chemistry keyword filtering.", "", "", "", "", ""],
  ["4", "PIDCon", "Use for graph recovery evaluation with box-line-connection-path annotations.", "", "", "", "", ""],
  ["5", "PID_dataset / Digitize-PID", "Use later for P&ID/PFD extension after storage and license checks.", "", "", "", "", ""],
];
summary.getRange("A12:A16").format = { fill: "#F4C95D", font: { bold: true }, horizontalAlignment: "center" };
summary.getRange("B12:B16").format = { font: { bold: true } };
summary.getRange("C12:H16").merge(true);
summary.getRange("A12:H16").format = { wrapText: true, verticalAlignment: "top" };

const scoreRows = records.map((record) => [
  record.name,
  Number(record.chem_relevance_score),
  Number(record.process_graph_fit_score),
  Number(record.combined_score),
  record.cleaned_use_tier,
  truncate(record.known_limitations, 90),
]);
summary.getRange("A19:F19").values = [["Dataset", "Chem score", "Graph score", "Combined", "Tier", "Main limitation"]];
summary.getRange(`A20:F${19 + scoreRows.length}`).values = scoreRows;
summary.getRange(`A19:F${19 + scoreRows.length}`).format = { wrapText: true };
summary.getRange("A19:F19").format = { fill: "#2F6F73", font: { color: "#FFFFFF", bold: true } };

const chart = summary.charts.add("bar", summary.getRange(`A19:D${19 + scoreRows.length}`));
chart.title = "Chemical and Graph-Fit Scores";
chart.hasLegend = true;
chart.xAxis = { axisType: "textAxis" };
chart.yAxis = { numberFormatCode: "0" };
chart.setPosition("H3", "N18");

review.getRangeByIndexes(0, 0, csvRows.length, csvRows[0].length).values = csvRows;
review.getRangeByIndexes(0, 0, 1, csvRows[0].length).format = {
  fill: "#17324D",
  font: { color: "#FFFFFF", bold: true },
  wrapText: true,
};
review.getRangeByIndexes(1, 0, csvRows.length - 1, csvRows[0].length).format = {
  wrapText: true,
  verticalAlignment: "top",
};
review.freezePanes.freezeRows(1);
review.tables.add(`A1:V${csvRows.length}`, true, "Task5DatasetReview");

const nodeTypes = schema.graph_record.nodes[0].type.map((type) => ["node_type", type]);
const edgeTypes = schema.graph_record.edges[0].type.map((type) => ["edge_type", type]);
const paramTypes = schema.graph_record.edges[0].parameters[0].type.map((type) => ["parameter_type", type]);
schemaSheet.getRange("A1:B1").values = [["Schema section", "Allowed value"]];
schemaSheet.getRange(`A2:B${1 + nodeTypes.length}`).values = nodeTypes;
schemaSheet.getRange(`D2:E${1 + edgeTypes.length}`).values = edgeTypes;
schemaSheet.getRange(`G2:H${1 + paramTypes.length}`).values = paramTypes;
schemaSheet.getRange("D1:E1").values = [["Schema section", "Allowed value"]];
schemaSheet.getRange("G1:H1").values = [["Schema section", "Allowed value"]];
schemaSheet.getRange("A1:B1").format = schemaSheet.getRange("D1:E1").format = schemaSheet.getRange("G1:H1").format = {
  fill: "#17324D",
  font: { color: "#FFFFFF", bold: true },
};

const sourceRows = records.map((record) => [
  record.name,
  record.source_url,
  record.download_url,
  record.license,
  record.next_actions,
]);
sources.getRange("A1:E1").values = [["Dataset", "Source URL", "Download URL", "License / access", "Next action"]];
sources.getRange(`A2:E${1 + sourceRows.length}`).values = sourceRows;
sources.getRange(`A1:E${1 + sourceRows.length}`).format = { wrapText: true, verticalAlignment: "top" };
sources.getRange("A1:E1").format = { fill: "#17324D", font: { color: "#FFFFFF", bold: true } };
sources.freezePanes.freezeRows(1);

const widths = {
  Summary: [120, 180, 230, 90, 120, 280, 20, 20],
  "Dataset Review": [100, 180, 110, 160, 160, 90, 90, 110, 90, 110, 90, 100, 90, 210, 260, 380, 320, 180, 260, 260, 320, 360],
  "Graph Schema": [130, 190, 20, 130, 180, 20, 130, 170],
  Sources: [180, 260, 260, 220, 360],
};
for (const [sheetName, sheetWidths] of Object.entries(widths)) {
  const sheet = workbook.worksheets.getItem(sheetName);
  sheetWidths.forEach((width, index) => {
    sheet.getRangeByIndexes(0, index, 1, 1).format.columnWidthPx = width;
  });
}

summary.getRange("A1:N32").format.verticalAlignment = "top";
summary.getRange("A1:N32").format.wrapText = true;

await fs.mkdir(outputDir, { recursive: true });

const errorScan = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 50 },
  summary: "final formula error scan",
});
console.log(errorScan.ndjson);

for (const sheetName of ["Summary", "Dataset Review", "Graph Schema", "Sources"]) {
  const preview = await workbook.render({
    sheetName,
    autoCrop: "all",
    scale: 1,
    format: "png",
  });
  await fs.writeFile(
    path.join(outputDir, `${sheetName.replaceAll(" ", "_").toLowerCase()}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`Wrote ${outputPath}`);
