from keras import regularizers
from keras.layers import Input
from keras.layers import Conv2D, Conv2DTranspose, UpSampling2D
from keras.activations import sigmoid
from keras.models import Model
from keras.layers import BatchNormalization
from keras.layers import concatenate
from keras.layers import LeakyReLU
from keras.layers.merge import add
from keras.layers import AveragePooling2D
from keras.utils import plot_model

def build_model( input_shape=(None, None, 1), output_channels=1, regular_factor=0.00001, initializer='he_normal', output_activation=sigmoid ):

    def make_activation( input_layer ):
        return LeakyReLU(alpha=0.2)(BatchNormalization(momentum=0.8)(input_layer))

    def make_block( input_layer, channels, kernel_size=(3,3) ):
        x = input_layer
        x = Conv2DTranspose( channels, kernel_size=kernel_size, activation='linear', strides=1, padding='valid', kernel_regularizer = kr, kernel_initializer = initializer )( x )
        x = make_activation( x )
        x = Conv2D( channels, kernel_size=kernel_size, activation='linear', strides=1, padding='valid', kernel_regularizer = kr, kernel_initializer = initializer )( x )
        x = make_activation( x )
        return x

    def make_output_block( input_layer, twin_channels, kernel_size, output_activation ):
        channels, output_channels = twin_channels
        x = input_layer
        x = Conv2DTranspose( channels, kernel_size=kernel_size, activation='linear', strides=1, padding='valid', kernel_regularizer = kr, kernel_initializer = initializer )( x )
        x = make_activation( x )
        x = Conv2D( output_channels, kernel_size=kernel_size, activation=output_activation, strides=1, padding='valid', kernel_regularizer = kr, kernel_initializer = initializer )( x )
        return x

    def make_pooling( input_layer ):
        return AveragePooling2D(pool_size=(2, 2))(input_layer)

    def make_upsampling( input_layer ):
        return UpSampling2D(size=(2, 2))( input_layer )

    def sum_up( input_layers ):
        return add( input_layers )

    def make_blocks( input_layer, channels, kernel_sizes ):
        sub_channels = int( channels/len(kernel_sizes) )
        assert sub_channels * len(kernel_sizes) == channels, 'sub-channels and channels not match, adjust the channels or the size of sub-kernels'
        layer_blocks = []
        for kernel_size in kernel_sizes:
            layer_blocks.append( make_block( input_layer, sub_channels, kernel_size ) )
        return concatenate( layer_blocks )


    kr = regularizers.l2( regular_factor )
    init = Input( input_shape )

    e_512 = make_blocks( init, 64, ((3, 3), (5, 5), (7, 7), (9, 9))  )
    e_256 = make_blocks( make_pooling(e_512), 128, ((3, 3), (5, 5), (7, 7), (9, 9))  )
    e_128 = make_blocks( make_pooling(e_256), 256, ((3, 3), (5, 5), (7, 7), (9, 9))  )
    e_64  = make_blocks( make_pooling(e_128), 512, ((3, 3), (5, 5), (7, 7), (9, 9))  )
    d_64 = e_64
    d_128 = add( [e_128, make_blocks( make_upsampling(d_64 ), 256, ((3, 3), (5, 5), (7, 7), (9, 9))  )] )
    d_256 = add( [e_256, make_blocks( make_upsampling(d_128), 128, ((3, 3), (5, 5), (7, 7), (9, 9))  )] )
    d_512 = add( [e_512, make_blocks( make_upsampling(d_256), 64,  ((3, 3), (5, 5), (7, 7), (9, 9))  )] )

    o_512 = make_output_block( d_512, (64,  output_channels), (9, 9), output_activation=output_activation )

    model = Model( inputs = init, outputs = o_512 )
    model.summary()

    return model

if __name__ == '__main__':
    mdcnn = build_model( (512, 512, 1), output_channels = 1 )
    plot_model(mdcnn, 'new_mdcnn_model.png', show_shapes=True, rankdir='TB')

