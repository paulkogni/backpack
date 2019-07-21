"""
BackPACK
"""
import torch
from .context import CTX


class backpack():
    """
    Context manager for the configuration of the backward pass.
    Activates the backprop extensions given as arguments within the context.
    """

    def __init__(self, *args):
        """
        Activate the Backpack extensions.

        Example usage:
        ```
        X, Y, model, lossfunc = get_problem()

        backpack.extend(model)
        backpack.extend(lossfunc)

        with backpack.backpack(backpack.extensions.Variance()):
            lossfunc(model(X), Y).backward()

            for p in model.parameters():
                print(p.grad)
                print(p.variance)
        ```

        .. warning ::

            The quantities computed by backPACK may be garbage collected when
            exiting the `with` clause. Use them within the `with` clause or
            assign them to another variable.

        Parameters:
            args: [BackpropExtension]
                The extensions to activate for the backward pass.
        """
        self.args = args

    def __enter__(self):
        self.old_CTX = CTX.get_active_exts()
        CTX.set_active_exts(self.args)

    def __exit__(self, type, value, traceback):
        CTX.set_active_exts(self.old_CTX)
        CTX.clear()


def extend(module, debug=True):
    """
    Extends the `module` to make it backPACK-ready.

    Attributes
    ----------
    module: torch.nn.Module
        The module to extend
    debug: Bool, optional (default: False)
        If true, will print debug messages during the extension and backward.
    """
    if debug:
        print("[DEBUG] Extending", module)

    for child in module.children():
        extend(child)

    def store_io(module, input, output):
        for i in range(len(input)):
            setattr(module, 'input{}'.format(i), input[i])
        setattr(module, 'output', output)

    def store_shapes(module, input, output):
        """Store dimensionality of output as buffer."""
        for i in range(len(input)):
            module.register_buffer(
                'input{}_shape'.format(i),
                torch.IntTensor([*input[i].size()])
            )
        module.register_buffer(
            'output_shape',
            torch.IntTensor([*output.size()])
        )

    def run_extensions(module_, g_inp, g_out):
        for backpack_extension in CTX.get_active_exts():
            if debug:
                print(
                    "[DEBUG] Running extension", backpack_extension,
                    "on ", module
                )
            backpack_extension.apply(module_, g_inp, g_out)

    CTX.add_hook_handle(module.register_forward_hook(store_io))
    CTX.add_hook_handle(module.register_forward_hook(store_shapes))
    CTX.add_hook_handle(module.register_backward_hook(run_extensions))

    return module
