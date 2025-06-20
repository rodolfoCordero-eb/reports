from sessions import Session
from single import Single
from actions import *
from draw import *
import argparse
import importlib

def mode_assume(strategy):
    print(f"🎇 Assume mode")
    session=Session()
    session.execute(strategy)

def mode_single(strategy,region=None):
    print(f"🎇 Single mode")
    single=Single()
    single.execute(strategy,region)

def load_strategy(class_name):
    try:
        module_name = "actions" if "action" in class_name else "draw"
        module = importlib.import_module(f"{module_name}.{class_name}")
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
    parser.add_argument("--region", required=False, default=None,
                        help="Region Anme")
    
    args = parser.parse_args()
    strategy = load_strategy(args.strategy)
    
    if args.mode == "single":
        mode_single(strategy,args.region)
    elif args.mode == "assume":
        mode_assume(strategy)

if __name__ == "__main__":
    print("\n✅ Starting...")
    main()
    print("\n✌️ Complete.")
    
