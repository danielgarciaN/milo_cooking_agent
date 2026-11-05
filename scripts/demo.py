"""Muestro preguntas, fragmentos recuperados, fuentes y respuestas reales."""

import argparse

from milo.rag import NutritionRAG, show_answer

QUESTIONS = [
    "¿Qué recomendaciones nutricionales hay para una dieta equilibrada?",
    "Recomiéndame una receta sencilla con pollo y arroz.",
    "¿Puedo sustituir arroz seco por el mismo peso de patata cruda?",
    "¿Cómo preparo una tortilla de espinacas?",
    "¿Puedo tratar un yogur sin lactosa como alternativa para una alergia a la leche?",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?")
    parser.add_argument("--agent", action="store_true", help="Demostración conversacional de LangGraph")
    args = parser.parse_args()
    if args.agent:
        from milo.agent import MiloAgent, show_turn

        agent = MiloAgent()
        questions = (
            [args.question]
            if args.question
            else [
                QUESTIONS[1],
                "¿Cuántas calorías y proteínas tiene esa receta?",
                "Ajústala a 600 kcal por ración.",
            ]
        )
        for question in questions:
            show_turn(agent.ask(question, thread_id="demo"))
        return
    rag = NutritionRAG()
    for question in [args.question] if args.question else QUESTIONS:
        show_answer(rag.ask(question))


if __name__ == "__main__":
    main()
