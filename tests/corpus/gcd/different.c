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