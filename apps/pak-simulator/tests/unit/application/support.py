from pak_simulator.model import Pak, Sessions, Simulation


def make_simulation(pak: Pak, sessions: Sessions) -> Simulation:
    return Simulation("http://backend", True, sessions, (pak,), (pak.profile,))
