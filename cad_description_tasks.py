from llm_judge import llm_judge

_describe_cube_10cm = llm_judge(
    prompt=(
        "CAD input:\n"
        "A cube with side length 10 cm.\n\n"
        "Describe what is in the CAD model."
    ),
    judge={
        "name": "describe-cube-10cm-judge",
        "task": "Score whether the response accurately describes the CAD input.",
        "criteria": [
            {
                "requirement": "The response identifies the object as a cube.",
                "weight": 0.5,
            },
            {
                "requirement": "The response says the cube has side length 10 cm, or an equivalent statement.",
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
_describe_cube_10cm.slug = "describe-cube-10cm"

tasks = [
    _describe_cube_10cm,
]
