def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

answer = factorial(4)
print(answer)
