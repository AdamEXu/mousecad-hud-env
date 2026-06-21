from __future__ import annotations

from textwrap import dedent


CAD_DSL_REFERENCE = dedent(
    """
    Python CAD DSL reference:
    - ref(kind, name) references an existing CAD object.
    - sketch(on, name, *, origin=(0, 0)) starts a sketch on a plane or planar face.
    - curve(sketch_ref, "line", name, start=(x, y), end=(x, y)) adds a line.
    - curve(sketch_ref, "circle", name, center=(x, y), radius=r) adds a circle.
    - done(sketch_ref) finishes a sketch.
    - profile(sketch_ref, name, *, hint=None) selects a closed region.
    - feature("extrude", profile_ref, body_name, distance=d, mode="new"|"add"|"cut"|"intersect") extrudes a body.

    Required generation rules:
    - Output exactly one tool call and no prose or markdown.
    - Put only executable Python CAD DSL code inside <parameter=template>.
    - Use the CAD functions above; do not import modules, define functions, or call any other Python APIs.
    - Use millimeters. 5 cm is 50 mm; 2 cm is 20 mm.
    - Use explicit line start/end points for polygon sketches.
    - Call done(sketch_ref) before profile(sketch_ref, ...).
    """
).strip()


OUTPUT_CONTRACT = dedent(
    """
    Output format:
    <tool_call>
    <function=predict_cad_template>
    <parameter=template>
    {template_history}
    </parameter>
    </function>
    </tool_call>
    """
).strip()


INPUT_TEMPLATE = dedent(
    """
    <task_type>
    predict_template_from_request
    </task_type>

    <user_request>
    {user_request}
    </user_request>

    <selection>
    {selection}
    </selection>

    <anchor>
    insert_before_id={feature_id}
    anchor_point={anchor_point}
    </anchor>

    <history>
    {history}
    </history>

    {cad_reference}

    {output_contract}
    """
).strip()


def build_prompt(
    user_request: str,
    *,
    selection: str = "",
    feature_id: str = "end",
    anchor_point: str = "",
    history: str = "",
) -> str:
    return INPUT_TEMPLATE.format(
        user_request=user_request,
        selection=selection,
        feature_id=feature_id,
        anchor_point=anchor_point,
        history=history,
        cad_reference=CAD_DSL_REFERENCE,
        output_contract=OUTPUT_CONTRACT,
    )
