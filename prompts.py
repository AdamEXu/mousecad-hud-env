JUDGE_SYSTEM_PROMPT = """You evaluate a CAD benchmark response against one criterion.

The benchmark may ask the model to describe CAD geometry or generate a CAD tool
call. Decide whether the response satisfies the criterion.

Return only raw JSON in this shape:
{"criterion_status":"MET","explanation":"Brief reason."}

Use MET when the response satisfies the criterion. For negative criteria, use
MET when the response makes the described mistake."""


CAD_SYSTEM_PROMPT = """MouseCAD decoding rules and API reference.

You are working with MouseCAD CAD benchmarks.

There are two related representations:

1. Verbose vector form
   This is the readable form of the normalized DeepCAD-style vector history.
   It is used as CAD input in description tasks.

2. Python stub form
   This is the model output DSL for CAD generation/edit tasks.
   It describes executable CAD intent with a small set of canonical calls.

Important rule: verbose vector numeric fields are encoded/discrete tokens unless
the task gives a task-specific physical decoding rule. Do not assume raw x/y/r
tokens are final millimeters. Do not assume e1 is directly millimeters.

Verbose vector raw row schema:
(cmd, x, y, alpha, f, r, theta, phi, gamma, px, py, pz, scale, e1, e2, b, u)

Command IDs:
- 0 = LINE
- 1 = ARC
- 2 = CIRCLE
- 3 = EOS
- 4 = SOL
- 5 = EXT

Verbose command syntax:
- SKETCH <sketch_id>
- <SOL> <sketch_id> <loop_id>
- L <sketch_id> <loop_id> x=<int> y=<int>
- A <sketch_id> <loop_id> x=<int> y=<int> alpha=<int> f=<0|1>
- C <sketch_id> <loop_id> x=<int> y=<int> r=<int>
- PROFILE <profile_id> sketch=<sketch_id> loops=<loop_id>[,<loop_id>...]
- E <extrude_id> sketch=<sketch_id> profile=<profile_id> theta=<int> phi=<int> gamma=<int> px=<int> py=<int> pz=<int> scale=<int> e1=<int> e2=<int> boolean=<mode> b=<int> extent=<extent> u=<int>
- <EOS>

Boolean modes:
- 0 = new_body
- 1 = join
- 2 = cut
- 3 = intersect

Verbose boolean names can also appear directly:
- new_body
- join
- cut
- intersect

Extent modes:
- 0 = one_sided
- 1 = symmetric
- 2 = two_sided

Identifier conventions:
- Global namespace: sketch_1, profile_1, extrude_1
- Patch namespace: patch_sketch_1, patch_profile_1, patch_extrude_1
- Loops: loop_1, loop_2, ...

Verbose parsing rules:
- <SOL> starts a new closed sketch loop.
- L, A, and C rows are appended to the current loop.
- PROFILE creates a face from one or more closed loops.
- E closes the current operation and binds all collected loops to one profile
  and one extrude.
- <EOS> ends the sequence.

Curve semantics:
- L is a line ending at (x, y).
- A is an arc ending at (x, y), with alpha and f controlling arc shape and
  direction.
- C is a circle centered at (x, y), with encoded radius r.
- A circle row can define a complete closed circular loop by itself.
- Each vector curve row stores the curve endpoint. For line and arc conversion,
  infer the start point from the previous curve endpoint. The first curve starts
  at the final curve endpoint, which closes the loop.

Extrude semantics:
- E/Pad extrudes the profile along the sketch normal.
- extent=one_sided means a one-sided extrusion from the sketch plane.
- theta, phi, gamma, px, py, pz, scale, e2, and extent are preserved in the
  verbose vector API even when the simplified Python stub does not expose them.
- b and u are vector fields preserved by the verbose form. The simplified
  Python stub usually expresses body intent through body_name and mode instead.
- Values of 128 in theta/phi/gamma/px/py/pz/scale/e2 are neutral/default
  placeholders unless the task says otherwise.

Python stub API:
- ref(kind: str, name: str)
- sketch(reference, name: str)
- curve(sketch_obj, curve_type: str, name: str, *, start=None, end=None, center=None, radius=None, mid=None)
- done(sketch_obj)
- profile(sketch_obj, name: str)
- feature(feature_type: str, profile_obj, body_name: str, *, distance: number, mode: str)

Allowed Python stub values:
- curve_type: line, arc, circle
- feature_type: extrude
- mode: new, add, cut, intersect

Boolean conversion from verbose vector to Python stub:
- new_body -> mode='new'
- join -> mode='add'
- cut -> mode='cut'
- intersect -> mode='intersect'

Extrude distance conversion from verbose vector token to Python stub distance:
distance = (e1 / 256 * 2 - 1) * 1000

For example:
- e1=50 converts to distance=-609.375 in the Python stub.
- e1=128 converts to distance=0.0 in the Python stub.

Python stub output conventions:
- Use ref('plane', 'plane_1') for a default base sketch plane unless the task
  asks for another reference.
- Create a sketch with sketch(...), create curves with curve(...), call
  done(sketch_obj), create profile(...), then create feature('extrude', ...).
- For line curves, include explicit start=(x, y) and end=(x, y).
- For circle curves, include center=(x, y) and radius=<number>.
- Keep names simple and deterministic. Follow task-specific required names
  exactly when a benchmark gives them.
- If a task asks for a tool call, output exactly the requested tool call wrapper
  and no prose. Do not wrap the tool call in markdown fences.

Python stub example for a rectangular prism, not a benchmark answer:
s1 = sketch(ref('plane', 'plane_1'), 'sketch_1')
e1 = curve(s1, 'line', 'e1', start=(0, 0), end=(10, 0))
e2 = curve(s1, 'line', 'e2', start=(10, 0), end=(10, 20))
e3 = curve(s1, 'line', 'e3', start=(10, 20), end=(0, 20))
e4 = curve(s1, 'line', 'e4', start=(0, 20), end=(0, 0))
done(s1)
p1 = profile(s1, 'profile_1')
b1 = feature('extrude', p1, 'body_1', distance=-500.0, mode='add')

Description task behavior:
- Describe the final CAD solid, not the command sequence.
- Identify basic solids from profiles and extrudes: a closed square/rectangle
  profile extruded one-sided is a box/prism; a circular profile extruded
  one-sided is a vertical cylinder.
- Use the task-specific physical dimensions when the prompt provides them.
- If no physical decoding rule is provided, avoid pretending encoded tokens are
  millimeters. Describe the shape and the encoded dimensions or converted stub
  distance only when useful.
- Do not hallucinate extra features such as holes, fillets, cuts, multiple
  bodies, or non-existent geometry.

Description examples:
- A loop made from L endpoints (0,0) -> (25,0) -> (25,25) -> (0,25) -> (0,0)
  is a closed square profile in encoded sketch coordinates.
- If a task says that 0..25 in sketch coordinates represents 50 mm and that
  the Pad token in that benchmark represents a 50 mm final extrusion, then the
  final object is a 50 mm x 50 mm x 50 mm cube.
- A C row such as C Sketch loop_1 x=0 y=0 r=20 creates a circular profile.
  Extruding that profile one-sided creates a vertical cylinder. If the task
  gives physical dimensions such as 40.20 mm diameter and 27.00 mm height, use
  those dimensions in the answer."""


MOUSECAD_DECODING_RULES = CAD_SYSTEM_PROMPT


DESCRIBE_CUBE_5CM_PROMPT = (
    f"{CAD_SYSTEM_PROMPT}\n\n"
    "Task-specific physical decoding for this benchmark:\n"
    "- The 0..25 square profile represents a 50 mm x 50 mm face.\n"
    "- The one-sided Pad with e1=50 represents a 50 mm final extrusion depth.\n\n"
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
    f"{CAD_SYSTEM_PROMPT}\n\n"
    "Task:\n"
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
