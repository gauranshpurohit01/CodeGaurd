int count_divisors(int n) {
    int cnt = 0;
    for (int i = 1; i <= n; i++) {
        if (n % i == 0) cnt = cnt + 1;
    }
    return cnt;
}