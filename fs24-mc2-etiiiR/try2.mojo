alias type = DType.float32
from random import rand
from algorithm import parallelize, vectorize
from memory import memset_zero
from algorithm import Static2DTileUnitFunc as Tile2DFunc
alias nelts = simdwidthof[type]() * 2

alias M = 512  # rows of A and C
alias N = 4096  # cols of B and C
alias K = 512  # cols of A and rows of B

struct Matrix[rows: Int, cols: Int]:
    var data: DTypePointer[type]

    # Initialize zeroing all values
    fn __init__(inout self):
        self.data = DTypePointer[type].alloc(rows * cols)
        memset_zero(self.data, rows * cols)

    # Initialize taking a pointer, don't set any elements
    fn __init__(inout self, data: DTypePointer[type]):
        self.data = data

    ## Initialize with random values
    @staticmethod
    fn rand() -> Self:
        var data = DTypePointer[type].alloc(rows * cols)
        rand(data, rows * cols)
        return Self(data)

    fn __getitem__(self, y: Int, x: Int) -> Scalar[type]:
        return self.load[1](y, x)

    fn __setitem__(inout self, y: Int, x: Int, val: Scalar[type]):
        self.store[1](y, x, val)

    fn load[nelts: Int](self, y: Int, x: Int) -> SIMD[type, nelts]:
        return self.data.load[width=nelts](y * self.cols + x)

    fn store[nelts: Int](self, y: Int, x: Int, val: SIMD[type, nelts]):
        self.data.store[width=nelts](y * self.cols + x, val)

# Parallelize the code by using the builtin parallelize function
fn matmul_parallelized(inout C: Matrix, A: Matrix, B: Matrix):
    @parameter
    fn calc_row(m: Int):
        for k in range(A.cols):
            @parameter
            fn dot[nelts: Int](n: Int):
                C.store[nelts](
                    m, n, C.load[nelts](m, n) + A[m, k] * B.load[nelts](k, n)
                )
            vectorize[dot, nelts, size = C.cols]()
    parallelize[calc_row](C.rows, C.rows)

struct SVDResult:
    var U: Matrix[M, M]
    var S: Matrix[M, N]
    var V: Matrix[N, N]

    fn __init__(inout self ,U: Matrix[M, M], S: Matrix[M, N], V: Matrix[N, N]):
        pass



# Function to perform SVD
fn svd(A: Matrix[M, K]) -> SVDResult:
    var U = Matrix[M, M]()
    var S = Matrix[M, K]()
    var V = Matrix[K, K]()
    

    # Step 1: Bidiagonalization (Householder transformations)
    # Placeholder for actual bidiagonalization logic
    # Here, you would implement the logic to reduce A to bidiagonal form

    # Step 2: Diagonalization of the bidiagonal matrix
    # Placeholder for iterative diagonalization logic (e.g., QR algorithm)
    # Here, you would implement the logic to diagonalize the bidiagonal matrix

    # Step 3: Assemble U, Σ, and V matrices
    # Placeholder for assembling the final matrices from the bidiagonal form

    return SVDResult(U, S, V)

fn main():
    var A = Matrix[M, K].rand()
    var B = Matrix[K, N].rand()
    var C = Matrix[M, N]()
    matmul_parallelized(C, A, B)
    print(C[0, 0])

    var svd_result = svd(A)
    var U = svd_result.U
    var S = svd_result.S
    var V = svd_result.V

    # Print or validate U, S, and V as needed
    print(U[0, 0], S[0, 0], V[0, 0])


# idk how to implement the svd function
# mojo still doesn't support the necessary operations
# so I'm just going to leave it as a placeholder