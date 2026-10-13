int factorial_while(int n) {
    int res = 1;
    int i = 1;
    while (i <= n) {
        res = res * i;
        i = i + 1;
    }
    return res;
}