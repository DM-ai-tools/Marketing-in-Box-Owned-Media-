import type { PlanNode } from "./planTree";

/**
 * Tidy horizontal tree layout: root on the left, one column per depth.
 *
 * Horizontal rather than the radial mind map the word suggests, because the labels are sentences.
 * A radial layout puts them at every angle, which either rotates the text or overlaps it, and a
 * plan's node titles ("CRO Audit & Enhanced Pillar Page Content") are the content — not decoration
 * around a shape. Left-to-right also matches how the plan reads: root, phases, assets, details.
 *
 * The algorithm is the standard simplification of Reingold-Tilford: walk the visible tree in order,
 * give every leaf the next free row, and place every parent at the mean of its children's rows.
 * That is O(n), never overlaps, and keeps siblings contiguous — which is what makes a phase's
 * assets read as one group.
 */

export const NODE_W = 208;
export const NODE_H = 40;
/** Column pitch. The gap is where the connector curve lives. */
export const COL_W = NODE_W + 48;
/** Row pitch. */
export const ROW_H = NODE_H + 12;

export interface PlacedNode {
  node: PlanNode;
  x: number;
  y: number;
  /** Whether this node has children that are currently hidden. */
  collapsed: boolean;
  hasChildren: boolean;
}

export interface PlanEdge {
  id: string;
  fromId: string;
  toId: string;
  /** Cubic bezier `d`, left edge of the parent's column to the child's left edge. */
  path: string;
}

export interface PlanLayout {
  nodes: PlacedNode[];
  edges: PlanEdge[];
  width: number;
  height: number;
}

function edgePath(px: number, py: number, cx: number, cy: number): string {
  const x1 = px + NODE_W;
  const y1 = py + NODE_H / 2;
  const y2 = cy + NODE_H / 2;
  // Control points half way across the gap, so the curve leaves and arrives horizontally. A
  // straight line would cross neighbouring nodes whenever a parent has many children.
  const mid = x1 + (cx - x1) / 2;
  return `M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${cx} ${y2}`;
}

/**
 * Place every visible node.
 *
 * `expanded` holds the ids whose children are shown. A node absent from it is collapsed, so the
 * default — an empty set — is a fully collapsed tree; callers seed it with the depths they want
 * open. Storing the *open* set rather than the closed one means a node added by a later
 * regeneration is closed by default rather than appearing already expanded.
 */
export function layoutPlan(root: PlanNode, expanded: Set<string>): PlanLayout {
  const nodes: PlacedNode[] = [];
  const edges: PlanEdge[] = [];
  let nextRow = 0;

  const place = (node: PlanNode): number => {
    const hasChildren = node.children.length > 0;
    const open = hasChildren && expanded.has(node.id);
    const x = node.depth * COL_W;

    let y: number;
    if (!open) {
      y = nextRow * ROW_H;
      nextRow += 1;
    } else {
      const childYs = node.children.map(place);
      y = (childYs[0] + childYs[childYs.length - 1]) / 2;
    }

    nodes.push({ node, x, y, collapsed: hasChildren && !open, hasChildren });

    if (open) {
      for (const child of node.children) {
        const placed = nodes.find((n) => n.node.id === child.id);
        if (placed) {
          edges.push({
            id: `${node.id}-${child.id}`,
            fromId: node.id,
            toId: child.id,
            path: edgePath(x, y, placed.x, placed.y),
          });
        }
      }
    }
    return y;
  };

  place(root);

  const width = Math.max(...nodes.map((n) => n.x + NODE_W), NODE_W) + 8;
  const height = Math.max(...nodes.map((n) => n.y + NODE_H), NODE_H) + 8;
  return { nodes, edges, width, height };
}

/** The chain of ids from the root down to `id`, for highlighting the path to the selected node. */
export function pathToNode(root: PlanNode, id: string): string[] {
  const trail: string[] = [];
  const walk = (node: PlanNode): boolean => {
    trail.push(node.id);
    if (node.id === id) return true;
    for (const child of node.children) if (walk(child)) return true;
    trail.pop();
    return false;
  };
  walk(root);
  return trail;
}

/** Every ancestor id of `id`, so revealing a search hit can open the branches above it. */
export function ancestorsOf(root: PlanNode, id: string): string[] {
  const trail = pathToNode(root, id);
  return trail.slice(0, -1);
}
