void reverse_string_for(char str[], int len) {
    for (int left = 0; left < len / 2; left++) {
        int right = len - left - 1;
        char temp = str[left];
        str[left] = str[right];
        str[right] = temp;
    }
}