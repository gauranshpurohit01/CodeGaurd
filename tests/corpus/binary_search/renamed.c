int search_key(int data[], int len, int key) {
    int l = 0;
    int r = len - 1;
    while (l <= r) {
        int m = (l + r) / 2;
        if (data[m] == key) return m;
        if (data[m] < key) {
            l = m + 1;
        } else {
            r = m - 1;
        }
    }
    return -1;
}