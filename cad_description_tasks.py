from llm_judge import llm_judge
from prompts import DESCRIBE_CUBE_5CM_PROMPT

_describe_cube_5cm = llm_judge(
    prompt=DESCRIBE_CUBE_5CM_PROMPT,
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
