import groq
import streamlit as st
import json

def load_model():
    try:
        client = groq.Client(api_key=st.secrets["groq_api_key"])
        return client
    except Exception as e:
        st.error(f"Error loading model: {e}")
        return None

def get_mindmap_output(question):
    """
    Generate a JSON response for mind map using Groq API, ensuring nodes and edges structure.
    """
    client = load_model()
    if client is None:
        return json.dumps({"nodes": [], "edges": []})  # Fallback empty JSON

    # Craft prompt to enforce JSON output
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
    If no valid structure can be generated, return: {{"nodes": [], "edges": []}}.
    """

    try:
        response = client.chat.completions.create(
            model="mistral-saba-24b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,  # Strict adherence for JSON
            max_tokens=1000   # Sufficient for mind map structure
        )
        raw_response = response.choices[0].message.content.strip()

        # Validate JSON
        try:
            data = json.loads(raw_response)
            if not isinstance(data, dict) or "nodes" not in data or "edges" not in data:
                st.warning("Invalid JSON structure. Using fallback.")
                return json.dumps({"nodes": [], "edges": []})

            # Ensure nodes have required fields
            for node in data["nodes"]:
                if not isinstance(node, dict):
                    st.warning(f"Invalid node: {node}. Using fallback.")
                    return json.dumps({"nodes": [], "edges": []})
                if "id" not in node:
                    node["id"] = f"node_{hash(str(node)) % 10000}"
                if "label" not in node:
                    node["label"] = "Unnamed"
                if "level" not in node:
                    node["level"] = 1
                    st.warning(f"Node {node['id']} missing 'level'. Set to 1.")

            # Validate edges
            node_ids = {node["id"] for node in data["nodes"]}
            valid_edges = [
                edge for edge in data["edges"]
                if isinstance(edge, dict) and edge.get("from") in node_ids and edge.get("to") in node_ids
            ]
            if len(valid_edges) < len(data["edges"]):
                st.warning("Some edges were invalid and removed.")
            data["edges"] = valid_edges

            return json.dumps(data)  # Return validated JSON as string

        except json.JSONDecodeError:
            st.error("Model returned invalid JSON. Using fallback.")
            return json.dumps({"nodes": [], "edges": []})

    except Exception as e:
        st.error(f"Error generating mind map response: {e}")
        return json.dumps({"nodes": [], "edges": []})