"""Script to generate the 8 problem families (32 source files) for the CodeGuard test corpus."""

import os
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"

CORPUS_DATA = {
    "factorial": {
        "original.c": """
int factorial(int n) {
    int res = 1;
    for (int i = 1; i <= n; i++) {
        res = res * i;
    }
    return res;
}
""",
        "renamed.c": """
int calc_fact(int num) {
    int ans = 1;
    for (int idx = 1; idx <= num; idx++) {
        ans = ans * idx;
    }
    return ans;
}
""",
        "restructured.c": """
int factorial_while(int n) {
    int res = 1;
    int i = 1;
    while (i <= n) {
        res = res * i;
        i = i + 1;
    }
    return res;
}
""",
        "different.c": """
int fibonacci(int n) {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}
"""
    },
    "fibonacci": {
        "original.c": """
int fibonacci(int n) {
    if (n <= 1) return n;
    int a = 0;
    int b = 1;
    for (int i = 2; i <= n; i++) {
        int c = a + b;
        a = b;
        b = c;
    }
    return b;
}
""",
        "renamed.c": """
int get_fib(int count) {
    if (count <= 1) return count;
    int prev = 0;
    int curr = 1;
    for (int step = 2; step <= count; step++) {
        int next_val = prev + curr;
        prev = curr;
        curr = next_val;
    }
    return curr;
}
""",
        "restructured.c": """
int fib_while(int n) {
    if (n <= 1) return n;
    int a = 0;
    int b = 1;
    int i = 2;
    while (i <= n) {
        int tmp = a + b;
        a = b;
        b = tmp;
        i = i + 1;
    }
    return b;
}
""",
        "different.c": """
int factorial_check(int n) {
    int product = 1;
    for (int k = 1; k <= n; k++) {
        product = product * k;
    }
    return product;
}
"""
    },
    "gcd": {
        "original.c": """
int gcd(int a, int b) {
    while (b != 0) {
        int rem = a % b;
        a = b;
        b = rem;
    }
    return a;
}
""",
        "renamed.c": """
int find_gcd(int num1, int num2) {
    while (num2 != 0) {
        int mod = num1 % num2;
        num1 = num2;
        num2 = mod;
    }
    return num1;
}
""",
        "restructured.c": """
int gcd_subtraction(int a, int b) {
    while (a != b) {
        if (a > b) {
            a = a - b;
        } else {
            b = b - a;
        }
    }
    return a;
}
""",
        "different.c": """
int lcm(int a, int b) {
    int max_val = (a > b) ? a : b;
    while (1) {
        if (max_val % a == 0 && max_val % b == 0) {
            return max_val;
        }
        max_val = max_val + 1;
    }
    return max_val;
}
"""
    },
    "prime_check": {
        "original.c": """
int is_prime(int n) {
    if (n <= 1) return 0;
    for (int i = 2; i * i <= n; i++) {
        if (n % i == 0) return 0;
    }
    return 1;
}
""",
        "renamed.c": """
int check_prime(int val) {
    if (val <= 1) return 0;
    for (int d = 2; d * d <= val; d++) {
        if (val % d == 0) return 0;
    }
    return 1;
}
""",
        "restructured.c": """
int is_prime_while(int n) {
    if (n <= 1) return 0;
    int d = 2;
    while (d * d <= n) {
        if (n % d == 0) return 0;
        d = d + 1;
    }
    return 1;
}
""",
        "different.c": """
int count_divisors(int n) {
    int cnt = 0;
    for (int i = 1; i <= n; i++) {
        if (n % i == 0) cnt = cnt + 1;
    }
    return cnt;
}
"""
    },
    "bubble_sort": {
        "original.c": """
void bubble_sort(int arr[], int n) {
    for (int i = 0; i < n - 1; i++) {
        for (int j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                int temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
            }
        }
    }
}
""",
        "renamed.c": """
void sort_array(int list[], int size) {
    for (int step = 0; step < size - 1; step++) {
        for (int idx = 0; idx < size - step - 1; idx++) {
            if (list[idx] > list[idx + 1]) {
                int swap_val = list[idx];
                list[idx] = list[idx + 1];
                list[idx + 1] = swap_val;
            }
        }
    }
}
""",
        "restructured.c": """
void bubble_sort_while(int arr[], int n) {
    int i = 0;
    while (i < n - 1) {
        int j = 0;
        while (j < n - i - 1) {
            if (arr[j] > arr[j + 1]) {
                int temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
            }
            j = j + 1;
        }
        i = i + 1;
    }
}
""",
        "different.c": """
int find_max(int arr[], int n) {
    int m = arr[0];
    for (int i = 1; i < n; i++) {
        if (arr[i] > m) {
            m = arr[i];
        }
    }
    return m;
}
"""
    },
    "binary_search": {
        "original.c": """
int binary_search(int arr[], int n, int target) {
    int low = 0;
    int high = n - 1;
    while (low <= high) {
        int mid = (low + high) / 2;
        if (arr[mid] == target) return mid;
        if (arr[mid] < target) {
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    return -1;
}
""",
        "renamed.c": """
int search_key(int data[], int len, int key) {
    int l = 0;
    int r = len - 1;
    while (l <= r) {
        int m = (l + r) / 2;
        if (data[m] == key) return m;
        if (data[m] < key) {
            l = m + 1;
        } else {
            r = m - 1;
        }
    }
    return -1;
}
""",
        "restructured.c": """
int binary_search_for(int arr[], int n, int target) {
    int low = 0;
    int high = n - 1;
    for (; low <= high; ) {
        int mid = (low + high) / 2;
        if (arr[mid] == target) return mid;
        if (arr[mid] < target) low = mid + 1;
        else high = mid - 1;
    }
    return -1;
}
""",
        "different.c": """
int linear_search(int arr[], int n, int target) {
    for (int i = 0; i < n; i++) {
        if (arr[i] == target) return i;
    }
    return -1;
}
"""
    },
    "array_sum": {
        "original.c": """
int array_sum(int arr[], int n) {
    int total = 0;
    for (int i = 0; i < n; i++) {
        total = total + arr[i];
    }
    return total;
}
""",
        "renamed.c": """
int calc_sum(int numbers[], int size) {
    int accum = 0;
    for (int idx = 0; idx < size; idx++) {
        accum = accum + numbers[idx];
    }
    return accum;
}
""",
        "restructured.c": """
int array_sum_while(int arr[], int n) {
    int total = 0;
    int i = 0;
    while (i < n) {
        total = total + arr[i];
        i = i + 1;
    }
    return total;
}
""",
        "different.c": """
int find_negative(int arr[], int n) {
    int idx = 0;
    while (idx < n) {
        if (arr[idx] < 0) return idx;
        idx = idx + 1;
    }
    return -1;
}
"""
    },
    "string_reverse": {
        "original.c": """
void reverse_string(char str[], int len) {
    int left = 0;
    int right = len - 1;
    while (left < right) {
        char temp = str[left];
        str[left] = str[right];
        str[right] = temp;
        left++;
        right--;
    }
}
""",
        "renamed.c": """
void invert_text(char buf[], int size) {
    int start = 0;
    int end = size - 1;
    while (start < end) {
        char ch = buf[start];
        buf[start] = buf[end];
        buf[end] = ch;
        start++;
        end--;
    }
}
""",
        "restructured.c": """
void reverse_string_for(char str[], int len) {
    for (int left = 0; left < len / 2; left++) {
        int right = len - left - 1;
        char temp = str[left];
        str[left] = str[right];
        str[right] = temp;
    }
}
""",
        "different.c": """
int string_length(char str[]) {
    int len = 0;
    while (str[len] != 0) {
        len++;
    }
    return len;
}
"""
    }
}


def generate_corpus():
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for family, variants in CORPUS_DATA.items():
        family_dir = CORPUS_DIR / family
        family_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in variants.items():
            file_path = family_dir / filename
            file_path.write_text(content.strip(), encoding="utf-8")
            count += 1
    print(f"Generated {count} corpus files across {len(CORPUS_DATA)} problem families in {CORPUS_DIR}")


if __name__ == "__main__":
    generate_corpus()
