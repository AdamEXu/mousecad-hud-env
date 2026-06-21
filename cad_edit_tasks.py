from llm_judge import llm_judge

_generate_cube_5cm = llm_judge(
    prompt=(
        "Generate a CAD template for a 5 cm cube.\n\n"
        "Output exactly one tool call and no prose. Use this wrapper:\n"
        "<tool_call>\n"
        "<function=generate_cad_template>\n"
        "<parameter=python_script>\n"
        "...python script...\n"
        "</parameter>\n"
        "</function>\n"
        "</tool_call>"
    ),
    judge={
        "name": "generate-cube-5cm-judge",
        "task": "Score whether the response generates the intended MouseCAD template for a 5 cm cube.",
        "expected_output": (
            "<tool_call>\n"
            "<function=generate_cad_template>\n"
            "<parameter=python_script>\n"
            "s1 = sketch(ref('plane', 'plane_1'), 'Sketch')\n"
            "e1 = curve(s1, 'line', 'e1', start=(0, 0), end=(25, 0))\n"
            "e2 = curve(s1, 'line', 'e2', start=(25, 0), end=(25, 25))\n"
            "e3 = curve(s1, 'line', 'e3', start=(25, 25), end=(0, 25))\n"
            "e4 = curve(s1, 'line', 'e4', start=(0, 25), end=(0, 0))\n"
            "done(s1)\n"
            "p1 = profile(s1, 'profile_1')\n"
            "b1 = feature('extrude', p1, 'body_1', distance=-609.375, mode='add')\n"
            "</parameter>\n"
            "</function>\n"
            "</tool_call>"
        ),
        "criteria": [
            {
                "requirement": "The response is exactly one tool call using function generate_cad_template with parameter python_script, not prose or markdown.",
                "weight": 0.2,
            },
            {
                "requirement": "The Python script creates sketch(ref('plane', 'plane_1'), 'Sketch').",
                "weight": 0.15,
            },
            {
                "requirement": "The Python script creates four line curves named e1 through e4 forming the closed square (0,0) -> (25,0) -> (25,25) -> (0,25) -> (0,0).",
                "weight": 0.25,
            },
            {
                "requirement": "The Python script calls done(s1) and creates profile(s1, 'profile_1').",
                "weight": 0.15,
            },
            {
                "requirement": "The Python script extrudes profile p1 into body_1 with distance=-609.375 and mode='add'.",
                "weight": 0.25,
            },
            {
                "type": "negative",
                "requirement": "The response adds extra geometry, uses apply_cad_edit, changes the coordinates, changes the body/profile/sketch names, changes the extrusion distance, or omits the required tool-call wrapper.",
                "weight": 0.5,
            },
        ],
    },
)
_generate_cube_5cm.slug = "generate-cube-5cm"

tasks = [
    _generate_cube_5cm,
]
