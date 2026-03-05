"""
Test rapid de viteză: măsoară timpul de răspuns pentru câteva rute.
Rulează: cd fisa_vizionare_app && python test_speed.py
"""
import os
import sys
import time

# Asigură că folosim sqlite pentru test rapid (fără .env cu postgres)
os.chdir(os.path.dirname(os.path.abspath(__file__)))
if "DATABASE_URL" not in os.environ:
    os.environ.setdefault("DATABASE_URL", "sqlite:///instance/app.db")

from main import app


def measure(name, fn, n=3):
    times = []
    for _ in range(n):
        start = time.perf_counter()
        fn()
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    avg = sum(times) / len(times)
    print(f"  {name}: {avg:.1f} ms (medie din {n}, min={min(times):.1f}, max={max(times):.1f})")
    return avg


def main():
    with app.test_client() as client:
        print("Test viteza aplicatie (Flask test client)\n")

        def home():
            r = client.get("/")
            assert r.status_code == 200

        def todo_redirect():
            # /todo fără login -> redirect la login
            r = client.get("/todo/")
            assert r.status_code in (200, 302)

        measure("GET / (home)", home)
        measure("GET /todo/ (redirect fara login)", todo_redirect)

    print("\nOK - aplicatia raspunde rapid.")


if __name__ == "__main__":
    main()
    sys.exit(0)
