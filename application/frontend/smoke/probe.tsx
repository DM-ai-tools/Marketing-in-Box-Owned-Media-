import { buildPlanTree, flattenPlan } from "../src/lib/planTree";
import { DEMO_PLAN } from "../src/pipeline/planFixture";

const t = buildPlanTree(DEMO_PLAN, "Sample Dental");
const all = flattenPlan(t.root);
console.log("--- shape (depth: title [kind] stars)");
for (const n of all.slice(0, 26)) {
  console.log(`${"  ".repeat(n.depth)}${n.depth}: ${n.title.slice(0, 46)} [${n.kind}]${n.stars ? " ★" + n.stars : ""}`);
}
console.log("\n--- funnel-ish nodes");
for (const n of all.filter((x) => /funnel/i.test(x.title))) {
  console.log(`  "${n.title}" kind=${n.kind} stars=${n.stars} bodyHead=${JSON.stringify(n.body.slice(0, 70))}`);
}
