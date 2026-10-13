int is_prime_while(int n) {
    if (n <= 1) return 0;
    int d = 2;
    while (d * d <= n) {
        if (n % d == 0) return 0;
        d = d + 1;
    }
    return 1;
}