int fibonacci(int n) {
    if (n <= 0) return 0;
    if (n == 1) return 1;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

int gcd(int a, int b) {
    if (b == 0) {
        return a;
    }
    return gcd(b, a % b);
}

int main() {
    int f5 = fibonacci(5);
    int f10 = fibonacci(10);
    int g = gcd(48, 18);

    printf("Fibonacci(5) = %d\n", f5);
    printf("Fibonacci(10) = %d\n", f10);
    printf("GCD(48, 18) = %d\n", g);
    return 0;
}
