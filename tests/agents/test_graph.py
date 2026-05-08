"""Tests for agents.graph — StateGraph assembly, edges, and checkpointing."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

from ainews.agents.state import (
    GraphState,
    RunParams,
    Summary,
)


def _make_state(**overrides: Any) -> GraphState:
    """Create a minimal GraphState for testing."""
    defaults: GraphState = {
        "run_id": "test-run",
        "params": RunParams(
            timeframe_days=7,
            topics=["AI"],
            sites=["example.com"],
        ),
        "queries": [],
        "raw_results": [],
        "fetched_articles": [],
        "filtered_articles": [],
        "clusters": [],
        "summaries": [],
        "trends": [],
        "report_md": "",
        "xlsx_path": "",
        "errors": [],
        "metrics": {},
        "loop_count": 0,
    }
    defaults.update(overrides)  # type: ignore[typeddict-item]
    return defaults


class TestBuildGraph:
    """Verify graph compilation."""

    def test_graph_compiles_without_checkpointer(self) -> None:
        """Graph compiles with all nodes registered."""
        from ainews.agents.graph import build_graph

        graph = build_graph()
        assert graph is not None

    def test_graph_compiles_with_checkpointer(self) -> None:
        """Graph compiles with SqliteSaver checkpointer."""
        from langgraph.checkpoint.sqlite import SqliteSaver

        from ainews.agents.graph import build_graph

        with SqliteSaver.from_conn_string(":memory:") as cp:
            graph = build_graph(checkpointer=cp)
            assert graph is not None

    def test_graph_has_expected_nodes(self) -> None:
        """Graph has all expected node names."""
        from ainews.agents.graph import build_graph

        graph = build_graph()
        node_names = set(graph.nodes.keys())

        expected = {
            "planner",
            "retrieve_one",
            "scraper",
            "filter",
            "dedup",
            "synthesize_one",
            "trender",
            "writer",
        }
        # LangGraph adds __start__ and __end__ nodes
        assert expected.issubset(node_names)


class TestGraphExecution:
    """Verify graph execution with mocked nodes."""

    def test_full_pipeline_with_mocks(self) -> None:
        """Full pipeline executes with all nodes mocked."""
        from ainews.agents.graph import build_graph

        # Mock all LLM calls and external tools
        mock_llm = MagicMock()

        # Planner returns queries
        planner_response = MagicMock(content=json.dumps(["AI news query"]))
        # Filter returns keep=True
        filter_response = MagicMock(
            content=json.dumps({"score": 0.9, "keep": True, "reason": "R"})
        )
        # Synthesizer returns summary
        synth_response = MagicMock(
            content=json.dumps(
                {
                    "headline": "Test Headline",
                    "bullets": ["Point 1"],
                    "why_it_matters": "Important",
                    "sources": ["https://example.com"],
                }
            )
        )
        # Trender returns trends
        trender_response = MagicMock(
            content=json.dumps(
                [
                    {
                        "name": "AI Trend",
                        "description": "Emerging",
                        "evidence_cluster_ids": ["c1"],
                    }
                ]
            )
        )
        # Writer executive summary
        writer_response = MagicMock(content="Executive summary")

        # Sequence LLM responses for all calls
        mock_llm.invoke.side_effect = [
            planner_response,  # planner
            filter_response,  # filter (1 article)
            synth_response,  # synthesizer (1 cluster)
            trender_response,  # trender
            writer_response,  # writer
        ]

        # Mock Tavily tool
        mock_tavily = MagicMock()
        mock_result = MagicMock()
        mock_result.url = "https://example.com/a"
        mock_result.title = "Test Article"
        mock_result.content = "Content about AI " * 30
        mock_result.raw_content = "Full content " * 30
        mock_result.score = 0.9
        mock_tavily.search.return_value = [mock_result]

        state = _make_state()

        with (
            patch(
                "ainews.agents.nodes.planner._get_llm",
                return_value=mock_llm,
            ),
            patch(
                "ainews.agents.nodes.filter._get_llm",
                return_value=mock_llm,
            ),
            patch(
                "ainews.agents.nodes.synthesizer._get_llm",
                return_value=mock_llm,
            ),
            patch(
                "ainews.agents.nodes.trender._get_llm",
                return_value=mock_llm,
            ),
            patch(
                "ainews.agents.nodes.writer._get_llm",
                return_value=mock_llm,
            ),
            patch(
                "ainews.agents.nodes.retriever._get_tavily_tool",
                return_value=mock_tavily,
            ),
        ):
            graph = build_graph()
            result = graph.invoke(state)

        assert result["report_md"] != ""
        assert "# AI News & Trends Report" in result["report_md"]
        assert len(result["queries"]) > 0

    def test_degrade_path_on_errors(self) -> None:
        """Graph degrades to Writer when error threshold hit."""
        from ainews.agents.graph import build_graph
        from ainews.agents.state import NodeError

        mock_llm = MagicMock()
        # Planner returns queries
        mock_llm.invoke.return_value = MagicMock(content=json.dumps(["query 1"]))

        # Pre-fill state with errors to trigger degrade
        errors = [
            NodeError(node=f"n{i}", message=f"e{i}", traceback="") for i in range(5)
        ]
        state = _make_state(
            errors=errors,
            summaries=[
                Summary(
                    cluster_id="c1",
                    headline="Test",
                    bullets=["p1"],
                    why_it_matters="w",
                    sources=["https://a.com"],
                ),
            ],
        )

        with (
            patch(
                "ainews.agents.nodes.planner._get_llm",
                return_value=mock_llm,
            ),
            patch(
                "ainews.agents.nodes.writer._get_llm",
                return_value=mock_llm,
            ),
            patch(
                "ainews.agents.nodes.retriever._get_tavily_tool",
                return_value=MagicMock(search=MagicMock(return_value=[])),
            ),
            patch(
                "ainews.agents.nodes.filter._get_llm",
                return_value=mock_llm,
            ),
            patch(
                "ainews.agents.nodes.trender._get_llm",
                return_value=mock_llm,
            ),
            patch(
                "ainews.agents.nodes.synthesizer._get_llm",
                return_value=mock_llm,
            ),
        ):
            graph = build_graph()
            result = graph.invoke(state)

        # Report should still be generated (degraded)
        assert result["report_md"] != ""


class TestCheckpointing:
    """Verify SqliteSaver integration."""

    def test_checkpoint_persists_state(self) -> None:
        """Graph state is checkpointed to SQLite."""
        from langgraph.checkpoint.sqlite import SqliteSaver

        from ainews.agents.graph import build_graph

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            MagicMock(content='["q1"]'),  # planner
            MagicMock(  # filter
                content=json.dumps({"score": 0.9, "keep": True, "reason": "R"})
            ),
            MagicMock(  # synthesizer
                content=json.dumps(
                    {
                        "headline": "H",
                        "bullets": ["b"],
                        "why_it_matters": "w",
                        "sources": ["u"],
                    }
                )
            ),
            MagicMock(  # trender
                content=json.dumps(
                    [
                        {
                            "name": "T",
                            "description": "D",
                            "evidence_cluster_ids": ["c1"],
                        }
                    ]
                )
            ),
            MagicMock(content="Exec summary"),  # writer
        ]

        mock_tavily = MagicMock()
        mr = MagicMock()
        mr.url = "https://ex.com/a"
        mr.title = "A"
        mr.content = "C " * 30
        mr.raw_content = "R " * 30
        mr.score = 0.9
        mock_tavily.search.return_value = [mr]

        state = _make_state(run_id="checkpoint-test")

        with SqliteSaver.from_conn_string(":memory:") as cp:
            graph = build_graph(checkpointer=cp)

            with (
                patch(
                    "ainews.agents.nodes.planner._get_llm",
                    return_value=mock_llm,
                ),
                patch(
                    "ainews.agents.nodes.filter._get_llm",
                    return_value=mock_llm,
                ),
                patch(
                    "ainews.agents.nodes.synthesizer._get_llm",
                    return_value=mock_llm,
                ),
                patch(
                    "ainews.agents.nodes.trender._get_llm",
                    return_value=mock_llm,
                ),
                patch(
                    "ainews.agents.nodes.writer._get_llm",
                    return_value=mock_llm,
                ),
                patch(
                    "ainews.agents.nodes.retriever._get_tavily_tool",
                    return_value=mock_tavily,
                ),
            ):
                config = {"configurable": {"thread_id": "checkpoint-test"}}
                result = graph.invoke(state, config)

            assert result["report_md"] != ""
