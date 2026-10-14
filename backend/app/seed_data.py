"""Seed script to populate CodeGuard database with realistic mock student submissions."""

import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.database import engine, Base, SessionLocal
from app.db.repository import SubmissionRepository
from app.db.models import Submission, FingerprintIndex


MOCK_SUBMISSIONS = [
    {
        "title": "HW1_Factorial_Alice.c",
        "language": "c",
        "source": """#include <stdio.h>

int factorial(int n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

int main(void) {
    int res = factorial(5);
    printf("%d\\n", res);
    return 0;
}
""",
    },
    {
        "title": "HW1_Factorial_Bob_Suspect.c",
        "language": "c",
        "source": """#include <stdio.h>

int compute_fact(int num) {
    int ans = 1;
    int i = 1;
    while (i <= num) {
        ans = ans * i;
        i = i + 1;
    }
    return ans;
}

int main(void) {
    int val = compute_fact(5);
    printf("%d\\n", val);
    return 0;
}
""",
    },
    {
        "title": "HW1_Factorial_Charlie.py",
        "language": "python",
        "source": """def factorial(n: int) -> int:
    res = 1
    for i in range(1, n + 1):
        res = res * i
    return res

def main() -> int:
    print(factorial(5))
    return 0
""",
    },
    {
        "title": "HW2_Fibonacci_David.java",
        "language": "java",
        "source": """public class FibonacciSolution {
    public static int fib(int n) {
        if (n <= 1) {
            return n;
        }
        int a = 0;
        int b = 1;
        for (int i = 2; i <= n; i = i + 1) {
            int c = a + b;
            a = b;
            b = c;
        }
        return b;
    }

    public static void main(String[] args) {
        System.out.println(fib(7));
    }
}
""",
    },
    {
        "title": "HW2_Fibonacci_Eve_Plagiarized.c",
        "language": "c",
        "source": """#include <stdio.h>

int get_fib_val(int count) {
    if (count <= 1) {
        return count;
    }
    int first = 0;
    int second = 1;
    int step = 2;
    while (step <= count) {
        int temp = first + second;
        first = second;
        second = temp;
        step = step + 1;
    }
    return second;
}

int main(void) {
    printf("%d\\n", get_fib_val(7));
    return 0;
}
""",
    },
    {
        "title": "HW3_BubbleSort_Frank.c",
        "language": "c",
        "source": """#include <stdio.h>

void bubble_sort(int arr[], int n) {
    for (int i = 0; i < n - 1; i = i + 1) {
        for (int j = 0; j < n - i - 1; j = j + 1) {
            if (arr[j] > arr[j + 1]) {
                int temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
            }
        }
    }
}

int main(void) {
    int data[5] = {64, 34, 25, 12, 22};
    bubble_sort(data, 5);
    printf("%d\\n", data[0]);
    return 0;
}
""",
    },
    {
        "title": "HW4_BinarySearch_Grace.c",
        "language": "c",
        "source": """#include <stdio.h>

int binary_search(int arr[], int n, int target) {
    int low = 0;
    int high = n - 1;
    while (low <= high) {
        int mid = (low + high) / 2;
        if (arr[mid] == target) {
            return mid;
        } else if (arr[mid] < target) {
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    return -1;
}

int main(void) {
    int nums[6] = {2, 5, 8, 12, 16, 23};
    int pos = binary_search(nums, 6, 12);
    printf("%d\\n", pos);
    return 0;
}
""",
    },
    {
        "title": "HW5_GCD_Heidi.py",
        "language": "python",
        "source": """def gcd(a: int, b: int) -> int:
    while b != 0:
        t = a % b
        a = b
        b = t
    return a

def main() -> int:
    print(gcd(48, 18))
    return 0
""",
    },
]


def seed_database():
    print("=" * 70)
    print("SEEDING CODEGUARD DATABASE WITH MOCK SUBMISSIONS")
    print("=" * 70)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Clear existing entries if any
        db.query(FingerprintIndex).delete()
        db.query(Submission).delete()
        db.commit()

        repo = SubmissionRepository(db)

        for item in MOCK_SUBMISSIONS:
            sub = repo.create_submission(
                title=item["title"],
                language=item["language"],
                source=item["source"].strip(),
            )
            print(f"Created Submission #{sub.id}: {sub.title} ({sub.language.upper()})")
            print(f"  -> Generated C Lines: {len(sub.generated_c_source.splitlines())}")
            print(f"  -> Token Fingerprints: {len(sub.token_fingerprints)}")
            print(f"  -> Subtree Hashes:     {len(sub.subtree_hashes)}")

        print("=" * 70)
        print(f"[SUCCESS] Successfully seeded {len(MOCK_SUBMISSIONS)} submissions into CodeGuard database!")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
