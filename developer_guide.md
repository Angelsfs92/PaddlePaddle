# Guide for developers

If you need to modify the algorithms/models in PaddleSpatial, you have to switch to the developer mode. The core algorithms of PaddleSpatial are mostly implemented in Python, but some also in C++, so you cannot develop PaddleSpatial simply with `pip install --editable {paddlespatial_path}`. To develop on your machine, please do the following:

1. Please follow the [installation guide](./installation_guide.md) to install all dependencies of PaddleSpatial (paddlepaddle >= 2.0.0rc0, pgl >= 1.2.0).

2. If you have already installed distributed PaddleSpatial with `pip install paddlespatial`, please uninstall it with:

    ```bash
    pip uninstall paddlespatial
    ```

3. Clone this repository to your local machine, supposed path at "/path_to_your_repo/":

    ```bash
    git clone https://github.com/PaddlePaddle/PaddleSpatial.git /path_to_your_repo/
    cd /path_to_your_repo/
    ```
4. If you want to change the algorithms in PaddleSpatial that are  implemented in Python, just find and modify corresponding `.py` files under the path "./paddlespatial", then add "/path_to_your_repo/" to your Python environment path:

    ```python
    import sys
    sys.path.append('/path_to_your_repo/')
    import paddlespatial
    ```

If you have any question or suggestion, feel free to create an [issue](https://github.com/PaddlePaddle/PaddleSpatial/issues). We will response as soon as possible.