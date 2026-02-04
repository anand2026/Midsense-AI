from dotenv import load_dotenv

from langgraph.graph import END, StateGraph

from graph.state import GraphState
from graph.consts import RETRIEVE, GENERATE, GRADE_DOCUMENTS, WEBSEARCH
from graph.chains import hallucination_grader, answer_grader, question_router
from graph.nodes import generate, grade_documents, retreive, web_search


load_dotenv()


def decide_to_generate(state):
    print("---ASSESS GRADED DOCUMENTS---")
    state["flow"].append("---ASSESS GRADED DOCUMENTS---")

    if state["use_web_search"]:
        print("---DECISION: NOT ALL DOCUMENTS ARE RELEVANT, GO TO WEB---")
        state["flow"].append("---DECISION: NOT ALL DOCUMENTS ARE RELEVANT, GO TO WEB---")
        return WEBSEARCH
    else:
        print("---DECISION: GENERATE---")
        state["flow"].append("---DECISION: GENERATE---")
        return GENERATE


def grade_generation_grounded_in_documents_and_question(state: GraphState):
    print("---CHECK HALLUCINATIONS---")
    state["flow"].append("---CHECK HALLUCINATIONS---")

    question = state["question"]
    documents = state["documents"]
    generation = state["generation"]

    score = hallucination_grader.hallucination_grader.invoke(
        {"documents": documents, "generation": generation}
    )
    if score.binary_score == "no":  # Answer generated is supported by facts retrived detected - means no hallucination
        print("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS---")
        state["flow"].append("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS---")
        return "not_supported"  # WEBSEARCH
    else:  # No hallucination (answer grounded/supported by documents)
        print("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
        print("---CHECK ANSWER---")
        state["flow"].append("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
        state["flow"].append("---CHECK ANSWER---")

        score = answer_grader.answer_grader.invoke({"question": question, "generation": generation})
        
        if score.binary_score == "yes":  # Answer is relevant
            print("---DECISION: ANSWER ADDRESSES THE USER QUESTION---")
            state["flow"].append("---DECISION: ANSWER ADDRESSES THE USER QUESTION---")
            return "useful"  # END
        else:  # Answer is not relevant
            print("---DECISION: ANSWER DOES NOT ADDRESS THE USER QUESTION---")
            state["flow"].append("---DECISION: ANSWER DOES NOT ADDRESS THE USER QUESTION---")
            return "not_useful"  # GENERATE


def route_question(state: GraphState):
    print("---ROUTE QUESTION---")
    state["flow"].append("---ROUTE QUESTION---")
    question = state["question"]

    source = question_router.question_router.invoke({"question": question})

    if source.datasource == WEBSEARCH:
        print("---DECISION: ROUTE QUESTION TO WEB SEARCH---")
        state["flow"].append("---DECISION: ROUTE QUESTION TO WEB SEARCH---")
        return WEBSEARCH
    elif source.datasource == "vectorstore":
        print("---DECISION: ROUTE QUESTION TO RAG---")
        state["flow"].append("---DECISION: ROUTE QUESTION TO RAG---")
        return RETRIEVE


flow = StateGraph(state_schema=GraphState)

flow.add_node(RETRIEVE, retreive.retrieve)
flow.add_node(GRADE_DOCUMENTS, grade_documents.grade_documents)
flow.add_node(GENERATE, generate.generate)
flow.add_node(WEBSEARCH, web_search.web_search)

flow.set_conditional_entry_point(
    route_question, path_map={RETRIEVE: RETRIEVE, WEBSEARCH: WEBSEARCH}
)

flow.add_edge(RETRIEVE, GRADE_DOCUMENTS)

flow.add_conditional_edges(
    GRADE_DOCUMENTS,
    decide_to_generate,
    path_map={WEBSEARCH: WEBSEARCH, GENERATE: GENERATE},
)
flow.add_conditional_edges(
    GENERATE,
    grade_generation_grounded_in_documents_and_question,
    path_map={"useful": END, "not_supported": WEBSEARCH, "not_useful": GENERATE},
)

flow.add_edge(WEBSEARCH, GENERATE)
flow.add_edge(GENERATE, END)

app = flow.compile()
# app.get_graph().draw_mermaid_png(output_file_path="graph.png")