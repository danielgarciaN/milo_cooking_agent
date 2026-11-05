"""Converso con MILO desde la terminal.

    python scripts/chat.py            # chat con el agente LangGraph (memoria + herramientas + RAG)
    python scripts/chat.py --rag      # solo RAG: muestra fragmentos recuperados y respuesta de Gemini
    python scripts/chat.py --hilo ana # retoma la conversación guardada con ese identificador
    python scripts/chat.py --borrar ana  # borra de la memoria solo esa conversación

Escribo "salir" para terminar.
"""

import argparse

from milo.agent import MiloAgent, show_turn
from milo.rag import NutritionRAG, show_answer


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--rag", action="store_true", help="Solo recuperación + generación, sin agente")
    parser.add_argument("--hilo", default="terminal", help="Identificador de la conversación (memoria)")
    parser.add_argument("--borrar", metavar="HILO", help="Borra una conversación de storage/memoria.sqlite")
    args = parser.parse_args()
    if args.borrar:
        from milo.agent import MiloAgent as Agent

        agent = Agent.__new__(Agent)  # Solo necesito la memoria: no cargo Gemini ni Chroma.
        Agent._memory(agent, None).delete_thread(args.borrar)
        print(f"Conversación '{args.borrar}' borrada. Las demás siguen guardadas.")
        return
    rag = NutritionRAG()
    agent = None if args.rag else MiloAgent(rag)
    print("MILO está listo. Escribe tu pregunta (o 'salir').\n")
    while True:
        try:
            question = input("Tú > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in {"salir", "exit", "quit"}:
            break
        if not question:
            continue
        if agent:
            show_turn(agent.ask(question, thread_id=args.hilo))
        else:
            show_answer(rag.ask(question))
        print("-" * 80)


if __name__ == "__main__":
    main()
