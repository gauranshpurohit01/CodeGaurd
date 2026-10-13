int find_gcd(int num1, int num2) {
    while (num2 != 0) {
        int mod = num1 % num2;
        num1 = num2;
        num2 = mod;
    }
    return num1;
}