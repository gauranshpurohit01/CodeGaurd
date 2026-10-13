"""AST Similarity Engine for CodeGuard.

Computes semantic and structural similarity between two abstract syntax trees using:
1. Recursive dynamic programming tree alignment (Dice-normalized LCS of ordered children)
2. Merkle-style subtree hashing (maximal matching subtrees with size >= 3)
3. Node size guards to guarantee fast execution on large trees.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple
from app.engine.ast_nodes import Node
from app.engine.winnowing import fnv1a_hash


SIZE_GUARD_THRESHOLD: int = 3000
MIN_SUBTREE_SIZE: int = 3


@dataclass
class MatchedSubtree:
    kind: str
    size: int
    line_a: int
    line_b: int
    hash_val: int


@dataclass
class ASTSimilarityReport:
    alignment_score: float
    coverage_a: float
    coverage_b: float
    mean_coverage: float
    overall_logic_similarity: float
    size_a: int
    size_b: int
    size_guard_triggered: bool
    matched_subtrees: List[MatchedSubtree] = field(default_factory=list)


class ASTSimilarityEngine:
    def __init__(self, size_guard: int = SIZE_GUARD_THRESHOLD, min_subtree_size: int = MIN_SUBTREE_SIZE) -> None:
        self.size_guard = size_guard
        self.min_subtree_size = min_subtree_size

    def compare(self, tree_a: Node, tree_b: Node) -> ASTSimilarityReport:
        size_a = tree_a.count_nodes()
        size_b = tree_b.count_nodes()

        # 1. Merkle Subtree Hashing
        hashes_a, sizes_a, nodes_by_hash_a = self._compute_subtree_hashes(tree_a)
        hashes_b, sizes_b, nodes_by_hash_b = self._compute_subtree_hashes(tree_b)

        common_hashes = set(nodes_by_hash_a.keys()).intersection(set(nodes_by_hash_b.keys()))

        # Extract maximal matching subtrees in A and B
        maximal_a = self._extract_maximal_subtrees(tree_a, common_hashes, hashes_a)
        maximal_b = self._extract_maximal_subtrees(tree_b, common_hashes, hashes_b)

        covered_a = sum(sizes_a[id(n)] for n in maximal_a)
        covered_b = sum(sizes_b[id(n)] for n in maximal_b)

        cov_a = min(1.0, covered_a / max(1, size_a))
        cov_b = min(1.0, covered_b / max(1, size_b))
        mean_cov = (cov_a + cov_b) / 2.0

        # Build list of matched subtrees
        matched_subtrees: List[MatchedSubtree] = []
        for n_a in maximal_a:
            h = hashes_a[id(n_a)]
            matching_b_nodes = nodes_by_hash_b.get(h, [])
            line_b = matching_b_nodes[0].line if matching_b_nodes else 0
            matched_subtrees.append(MatchedSubtree(
                kind=n_a.kind,
                size=sizes_a[id(n_a)],
                line_a=n_a.line,
                line_b=line_b,
                hash_val=h,
            ))

        # 2. Tree Alignment DP
        size_guard_triggered = (size_a > self.size_guard or size_b > self.size_guard)
        if size_guard_triggered:
            # Skip alignment when tree is excessively large; rely strictly on subtree hashing
            alignment_score = 0.0
            overall = mean_cov
        else:
            memo: Dict[Tuple[int, int], float] = {}
            matched_score = self._align(tree_a, tree_b, memo)
            alignment_score = (2.0 * matched_score) / (size_a + size_b)
            alignment_score = min(1.0, max(0.0, alignment_score))
            overall = max(alignment_score, mean_cov)

        return ASTSimilarityReport(
            alignment_score=alignment_score,
            coverage_a=cov_a,
            coverage_b=cov_b,
            mean_coverage=mean_cov,
            overall_logic_similarity=overall,
            size_a=size_a,
            size_b=size_b,
            size_guard_triggered=size_guard_triggered,
            matched_subtrees=matched_subtrees,
        )

    # -------------------------------------------------------------------------
    # Tree Alignment (Weighted DP)
    # -------------------------------------------------------------------------

    def _align(self, a: Node, b: Node, memo: Dict[Tuple[int, int], float]) -> float:
        """Recursive DP alignment of ordered children (LCS-style, weighted)."""
        key = (id(a), id(b))
        if key in memo:
            return memo[key]

        if a.kind != b.kind:
            memo[key] = 0.0
            return 0.0

        # Same kind gives full credit if value matches, else 0.5
        base_match = 1.0 if a.value == b.value else 0.5

        if not a.children or not b.children:
            memo[key] = base_match
            return base_match

        m, n = len(a.children), len(b.children)
        dp = [[0.0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                child_a = a.children[i - 1]
                child_b = b.children[j - 1]
                match_val = self._align(child_a, child_b, memo)
                dp[i][j] = max(
                    dp[i - 1][j],
                    dp[i][j - 1],
                    dp[i - 1][j - 1] + match_val,
                )

        score = base_match + dp[m][n]
        memo[key] = score
        return score

    # -------------------------------------------------------------------------
    # Merkle Subtree Hashing
    # -------------------------------------------------------------------------

    def _compute_subtree_hashes(
        self, root: Node
    ) -> Tuple[Dict[int, int], Dict[int, int], Dict[int, List[Node]]]:
        """Compute Merkle hashes and subtree sizes for all nodes in the tree."""
        hashes: Dict[int, int] = {}
        sizes: Dict[int, int] = {}
        nodes_by_hash: Dict[int, List[Node]] = {}

        def traverse(node: Node) -> Tuple[int, int]:
            child_hashes: List[int] = []
            subtree_size = 1
            for child in node.children:
                ch_hash, ch_size = traverse(child)
                child_hashes.append(ch_hash)
                subtree_size += ch_size

            # Merkle hash combining kind, normalized value, and child hashes
            raw_hash_str = f"{node.kind}:{node.value}:" + ",".join(str(h) for h in child_hashes)
            node_hash = fnv1a_hash(raw_hash_str)

            node_id = id(node)
            hashes[node_id] = node_hash
            sizes[node_id] = subtree_size

            if subtree_size >= self.min_subtree_size:
                nodes_by_hash.setdefault(node_hash, []).append(node)

            return node_hash, subtree_size

        traverse(root)
        return hashes, sizes, nodes_by_hash

    def _extract_maximal_subtrees(
        self, root: Node, common_hashes: Set[int], hashes: Dict[int, int]
    ) -> List[Node]:
        """Find top-level matched subtrees without double counting nested children."""
        maximal: List[Node] = []

        def dfs(node: Node) -> None:
            node_id = id(node)
            node_hash = hashes.get(node_id)
            if node_hash in common_hashes:
                # Maximal matching subtree found; do not descend into children
                maximal.append(node)
                return

            for child in node.children:
                dfs(child)

        dfs(root)
        return maximal


def compute_ast_similarity(tree_a: Node, tree_b: Node) -> ASTSimilarityReport:
    """Convenience helper to compute AST similarity."""
    engine = ASTSimilarityEngine()
    return engine.compare(tree_a, tree_b)
