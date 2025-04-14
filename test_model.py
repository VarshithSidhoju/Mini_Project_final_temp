import groq
import streamlit as st
import json
import logging

# Set up logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_model():
    """Load the Groq API client with the API key from Streamlit secrets."""
    try:
        client = groq.Client(api_key=st.secrets["groq_api_key"])
        return client
    except Exception as e:
        st.error(f"Error loading model: {e}")
        logger.error(f"Error loading model: {e}")
        return None

def get_output(question):
    """
    Generate a response using the Groq API and ensure it returns a valid JSON string
    with nodes (id, label, level) and edges (from, to).
    """
    client = load_model()
    if client is None:
        st.error("Failed to load model.")
        return json.dumps({"nodes": [], "edges": []})  # Fallback empty JSON

    # Craft a stricter prompt to enforce JSON output
    prompt = f"""
    {question}

    Ensure the response is a valid JSON object with:
    - "nodes": a list of objects, each with "id" (unique string), "label" (string), and "level" (integer, 0 for main topics, 1 for subtopics).
    - "edges": a list of objects with "from" (source node id) and "to" (target node id).
    Return ONLY the JSON object, no additional text, markdown, or code blocks.
    Example:
    {{
        "nodes": [
            {{"id": "topic", "label": "Main Topic", "level": 0}},
            {{"id": "topic_sub1", "label": "Subtopic 1", "level": 1}}
        ],
        "edges": [
            {{"from": "topic", "to": "topic_sub1"}}
        ]
    }}
    If no valid structure can be generated, return an empty structure: {{"nodes": [], "edges": []}}.
    """

    try:
        # Call the Groq API
        response = client.chat.completions.create(
            model="mistral-saba-24b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # Lower temperature for consistent JSON output
            max_tokens=1000   # Adjust based on expected response size
        )
        raw_response = response.choices[0].message.content.strip()
        logger.info(f"Raw response: {repr(raw_response)}")

        # Attempt to parse as JSON
        try:
            data = json.loads(raw_response)
        except json.JSONDecodeError as e:
            st.error(f"Model returned invalid JSON: {e}")
            logger.error(f"Invalid JSON: {raw_response}")
            # Return fallback JSON
            return json.dumps({
                "nodes": [{"id": "default", "label": "Default Topic", "level": 0}],
                "edges": []
            })

        # Validate and fix JSON structure
        if not isinstance(data, dict) or "nodes" not in data or "edges" not in data:
            st.warning("Model response missing 'nodes' or 'edges'. Using fallback.")
            logger.warning(f"Invalid structure: {data}")
            return json.dumps({
                "nodes": [{"id": "default", "label": "Default Topic", "level": 0}],
                "edges": []
            })

        # Ensure nodes have required fields
        for node in data["nodes"]:
            if not isinstance(node, dict):
                st.warning(f"Invalid node: {node}. Using fallback.")
                logger.warning(f"Invalid node: {node}")
                return json.dumps({
                    "nodes": [{"id": "default", "label": "Default Topic", "level": 0}],
                    "edges": []
                })
            if "id" not in node:
                node["id"] = f"node_{hash(str(node)) % 10000}"
            if "label" not in node:
                node["label"] = "Unnamed"
            if "level" not in node:
                node["level"] = 1  # Default to subtopic
                st.warning(f"Node {node['id']} missing 'level'. Set to 1.")
                logger.warning(f"Node {node['id']} missing 'level'.")

        # Validate edges
        node_ids = {node["id"] for node in data["nodes"]}
        valid_edges = [
            edge for edge in data["edges"]
            if isinstance(edge, dict) and edge.get("from") in node_ids and edge.get("to") in node_ids
        ]
        if len(valid_edges) < len(data["edges"]):
            st.warning("Some edges were invalid and removed.")
            logger.warning(f"Original edges: {data['edges']}, Valid edges: {valid_edges}")
        data["edges"] = valid_edges

        # Return validated JSON as string
        return json.dumps(data)

    except Exception as e:
        st.error(f"Error generating response: {e}")
        logger.error(f"Error generating response: {e}")
        return json.dumps({
            "nodes": [{"id": "default", "label": "Default Topic", "level": 0}],
            "edges": []
        })