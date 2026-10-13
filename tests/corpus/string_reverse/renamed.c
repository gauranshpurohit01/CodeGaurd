void invert_text(char buf[], int size) {
    int start = 0;
    int end = size - 1;
    while (start < end) {
        char ch = buf[start];
        buf[start] = buf[end];
        buf[end] = ch;
        start++;
        end--;
    }
}