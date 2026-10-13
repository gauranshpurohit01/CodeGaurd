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