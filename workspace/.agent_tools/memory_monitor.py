import json
import sys

import psutil


def main():
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    result = {
        "virtual_memory": {
            "total_gb": round(vm.total / 1024**3, 2),
            "used_gb": round(vm.used / 1024**3, 2),
            "available_gb": round(vm.available / 1024**3, 2),
            "percent_used": vm.percent,
        },
        "swap": {
            "total_gb": round(swap.total / 1024**3, 2),
            "used_gb": round(swap.used / 1024**3, 2),
            "percent_used": swap.percent,
        },
        "top_processes_by_memory": [
            {
                "pid": p.info["pid"],
                "name": p.info["name"],
                "rss_mb": round(p.info["memory_info"].rss / 1024**2, 1),
                "percent": p.info["memory_percent"],
            }
            for p in sorted(
                psutil.process_iter(["pid", "name", "memory_info", "memory_percent"]),
                key=lambda p: p.info["memory_info"].rss,
                reverse=True,
            )[:10]
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
