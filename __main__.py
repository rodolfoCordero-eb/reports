from sessions import Session
from single import Single
from actions import *
import argparse
import importlib

def mode_assume(strategy):
    print(f"🎇 Assume mode")
    session=Session()
    session.execute(strategy)

def mode_single(strategy):
    print(f"🎇 Single mode")
    single=Single()
    single.execute(strategy)

def load_strategy(class_name):
    try:
        module = importlib.import_module(f"actions.{class_name}")
        clase = getattr(module, class_name)
        return clase()
    except (ImportError, AttributeError) as e:
        raise ValueError(f"❌ Strategy '{class_name}' doesn't found: {e}")

def main():
    parser = argparse.ArgumentParser(description="Seleccionar modo de ejecución")
    parser.add_argument("--mode", choices=["single", "assume"],
                         required=True, help="ExcepcutionMode: 'single' o 'assume'")
    parser.add_argument("--strategy", required=True,
                        help="Name of class")
    
    args = parser.parse_args()
    strategy = load_strategy(args.strategy)
    if args.mode == "single":
        mode_single(strategy)
    elif args.mode == "assume":
        mode_assume(strategy)

if __name__ == "__main__":
    print("\n✅ Starting...")
    main()
    print("\n✌️ Complete.")
    
