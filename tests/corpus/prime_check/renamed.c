int check_prime(int val) {
    if (val <= 1) return 0;
    for (int d = 2; d * d <= val; d++) {
        if (val % d == 0) return 0;
    }
    return 1;
}