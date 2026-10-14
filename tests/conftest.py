import os
import sys

# чтобы pytest видел пакеты core/, storage/, services/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

