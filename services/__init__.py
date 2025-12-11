"""
Re-export functions from root services.py for backwards compatibility.
"""
import importlib.util
import os

# Load the root services.py module with a different name to avoid circular import
services_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'services.py')
spec = importlib.util.spec_from_file_location("_root_services", services_path)
root_services = importlib.util.module_from_spec(spec)
spec.loader.exec_module(root_services)

# Re-export functions
calculate_production_cost = root_services.calculate_production_cost
find_arbitrage = root_services.find_arbitrage
format_time = root_services.format_time

__all__ = ['calculate_production_cost', 'find_arbitrage', 'format_time']
