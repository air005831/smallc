void increment(int *ptr) {
    *ptr = *ptr + 1;
}

int main() {
    int x = 42;
    int *p = &x;
    int arr[5];
    int *ap;

    printf("Original: x = %d, *p = %d\n", x, *p);
    
    *p = 99;
    printf("After direct dereference edit: x = %d\n", x);
    
    increment(&x);
    printf("After increment function call: x = %d\n", x);
    
    // Pointer Arithmetic
    arr[0] = 100;
    arr[1] = 200;
    arr[2] = 300;
    
    ap = arr;
    printf("ap points to arr[0]: *ap = %d\n", *ap);
    ap = ap + 1;
    printf("ap + 1 points to arr[1]: *ap = %d\n", *ap);
    ap += 1;
    printf("ap += 1 points to arr[2]: *ap = %d\n", *ap);
    
    return 0;
}
