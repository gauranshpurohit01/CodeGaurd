int factorial_check(int n) {
    int product = 1;
    for (int k = 1; k <= n; k++) {
        product = product * k;
    }
    return product;
}