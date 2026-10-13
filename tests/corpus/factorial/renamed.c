int calc_fact(int num) {
    int ans = 1;
    for (int idx = 1; idx <= num; idx++) {
        ans = ans * idx;
    }
    return ans;
}