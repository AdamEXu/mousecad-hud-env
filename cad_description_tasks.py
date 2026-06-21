from llm_judge import llm_judge

_describe_cube_5cm = llm_judge(
    prompt=(
        "CAD input:\n"
        "SKETCH Sketch ; <SOL> Sketch loop_1 ; L Sketch loop_1 x=25 y=0 ; L Sketch loop_1 x=25 y=25 ; L Sketch loop_1 x=0 y=25 ; L Sketch loop_1 x=0 y=0 ; PROFILE profile_1 sketch=Sketch loops=loop_1 ; E Pad sketch=Sketch profile=profile_1 theta=128 phi=128 gamma=128 px=128 py=128 pz=128 scale=128 e1=50 e2=128 boolean=join b=1 extent=one_sided u=0 ; <EOS>\n\n"
        "Describe what is in the CAD model."
    ),
    judge={
        "name": "describe-cube-5cm-judge",
        "task": "Score whether the response accurately describes the CAD input.",
        "criteria": [
            {
                "requirement": "The response identifies the object as a cube.",
                "weight": 0.5,
            },
            {
                "requirement": "The response says the cube has side length 5 cm, or an equivalent statement.",
                "weight": 0.5,
            },
            {
                "type": "negative",
                "requirement": "The response hallucinates extra CAD features such as holes, cuts, fillets, multiple bodies, or non-cube geometry.",
                "weight": 0.25,
            },
        ],
    },
)
_describe_cube_5cm.slug = "describe-cube-5cm"

tasks = [
    _describe_cube_5cm,
]
