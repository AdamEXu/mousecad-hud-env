JUDGE_SYSTEM_PROMPT = """You evaluate a CAD benchmark response against one criterion.

The benchmark may ask the model to describe CAD geometry or generate a CAD tool
call. Decide whether the response satisfies the criterion.

Return only raw JSON in this shape:
{"criterion_status":"MET","explanation":"Brief reason."}

Use MET when the response satisfies the criterion. For negative criteria, use
MET when the response makes the described mistake."""


MOUSECAD_DECODING_RULES = """MouseCAD decoding rules:
- MouseCAD token coordinates are encoded CAD units. Do not assume raw x/y/r tokens are final physical mm unless a task-specific rule says so.
- L commands define line vertices in the sketch plane.
- C commands define circular sketch loops: x/y is the center and r is the encoded radius.
- PROFILE creates a face from closed sketch loops.
- E/Pad extrudes the profile one-sided along the sketch normal when extent=one_sided.
- e1 is the extrusion depth in mm.
- theta/phi/gamma/px/py/pz/scale/e2 values of 128 are neutral/default placeholders unless otherwise specified.
- Describe the final solid, not the command sequence."""


DESCRIBE_CUBE_5CM_PROMPT = (
    f"{MOUSECAD_DECODING_RULES}\n"
    "- For this benchmark, the 0..25 square profile represents a 50 mm x 50 mm face.\n\n"
    "CAD input:\n"
    "SKETCH Sketch ; <SOL> Sketch loop_1 ; L Sketch loop_1 x=25 y=0 ; "
    "L Sketch loop_1 x=25 y=25 ; L Sketch loop_1 x=0 y=25 ; "
    "L Sketch loop_1 x=0 y=0 ; PROFILE profile_1 sketch=Sketch loops=loop_1 ; "
    "E Pad sketch=Sketch profile=profile_1 theta=128 phi=128 gamma=128 "
    "px=128 py=128 pz=128 scale=128 e1=50 e2=128 boolean=join b=1 "
    "extent=one_sided u=0 ; <EOS>\n\n"
    "Describe what is in the CAD model."
)


GENERATE_CUBE_5CM_PROMPT = (
    "Generate a CAD template for a 5 cm cube.\n\n"
    "Output exactly one tool call and no prose. Use this wrapper:\n"
    "<tool_call>\n"
    "<function=generate_cad_template>\n"
    "<parameter=python_script>\n"
    "...python script...\n"
    "</parameter>\n"
    "</function>\n"
    "</tool_call>"
)


GENERATE_CUBE_5CM_EXPECTED_OUTPUT = (
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
)
