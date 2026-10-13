int find_negative(int arr[], int n) {
    int idx = 0;
    while (idx < n) {
        if (arr[idx] < 0) return idx;
        idx = idx + 1;
    }
    return -1;
}