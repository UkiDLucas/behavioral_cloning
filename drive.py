
# coding: utf-8

# # How to run the simulator
# $ python drive.py model.h5

# In[1]:


data_dir = "../_DATA/CarND_behavioral_cloning/r_001/"
image_final_width = 64
driving_data_csv = "driving_log_normalized.csv"
processed_images_dir = "processed_images/"

model_dir = "../_DATA/MODELS/"
model_name = "model_p3_14x64x3__epoch_70_val_acc_0.367285497303.h5"
model_path = model_dir + model_name
autorun_dir = data_dir + "autonomous_run/"
sample_autorun_image = "image_11.986971139907837.jpg"


# In[2]:

import argparse
import base64
import json
import numpy as np
import time
import eventlet
import eventlet.wsgi
import tensorflow as tf
import socketio
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

from PIL import Image
from PIL import ImageOps
from flask import Flask, render_template
from io import BytesIO
from keras.models import load_model
from keras.preprocessing.image import ImageDataGenerator, array_to_img, img_to_array

# if says Using Theano backend.
# $ edit ~/.keras/keras.json
# change to: "backend": "tensorflow",


# In[3]:

# https://github.com/fchollet/keras/issues/3857
tf.python.control_flow_ops = tf


# In[4]:

from DataHelper import create_steering_classes
steering_classes = create_steering_classes(number_of_classes = 41)


# In[5]:

def load_and_compile_model():
    from keras.models import load_model
    model = load_model(model_path) # should start at 60% acc.
   
    optimizer='sgd' # | 'rmsprop'
    loss_function="mse" # | 'binary_crossentropy' | 'mse' | mean_squared_error | sparse_categorical_crossentropy
    metrics_array=['accuracy'] # , mean_pred, false_rates

    model.compile(optimizer, loss_function, metrics_array)
    return model
    


# # Test model loading

# In[6]:

model = load_and_compile_model()
model.summary()


# In[7]:

from DataHelper import predict_class
    
def predict_steering(image_array, old_steering_angle):

    predictions = model.predict( image_array[None, :, :], batch_size=1, verbose=1)
    new_steering_angle = predict_class(predictions, steering_classes)
     
    # TODO compare to old_steering    
    #print("new_steering_angle", new_steering_angle)
    return new_steering_angle 


# # Test prediction
from ImageHelper import read_image_array
image_path = autorun_dir + sample_autorun_image
image = read_image_array(image_path)
print("image shape", image.shape)
plt.imshow(image)
plt.show()

new_steering_angle = predict_steering(image, 0.0)
print("new_steering_angle", new_steering_angle)
# In[8]:

def preprocess_image(image_string, elapsed_seconds):   
    
    from scipy.misc import imsave
    from ImageHelper import preprocessing_pipline
    
    image_jpg = Image.open(BytesIO(base64.b64decode(image_string)))
    image_array = preprocessing_pipline(image_jpg, final_size=image_final_width, 
                                        should_plot=False)
    
    # SAVE ONLY to review that pre-processing worked
    imsave(data_dir + "autonomous_run/image_" + str(elapsed_seconds) + ".jpg", image_array)
    return image_array


# In[9]:

sio = socketio.Server()
app = Flask(__name__)
model = None
prev_image_array = None

def send_control(steering_angle=0.0, throttle=0.2):
    sio.emit("steer", data={
    'steering_angle': steering_angle.__str__(),
    'throttle': throttle.__str__()
    }, skip_sid=True)
# In[10]:

def send_control(steering_angle=0.0, throttle=0.2):
    sio.emit("steer", data={
    'steering_angle': str(steering_angle),
    'throttle': throttle.__str__()
    }, skip_sid=True)


# In[ ]:

@sio.on('connect')
def connect(sid, environ):
    print("connect ", sid)
    send_control(0, 0)


# In[11]:

t0 = time.time()

@sio.on('telemetry')
def telemetry(sid, data):
    with open("output.txt", "a") as myfile:
        elapsed_seconds = time.time()-t0
        
        # The current values
        old_steering_angle = data["steering_angle"]
        throttle = data["throttle"]
        speed = data["speed"]

        # The current image from the center camera of the car
        image_array = preprocess_image(data["image"], elapsed_seconds)
        steering_angle = predict_steering(image_array, old_steering_angle)
        
        new_throttle = 0.1
        
        output = []
        output.append(str(round(float(elapsed_seconds),2)) + "\t")
        output.append(str(round(float(speed),2)) + "\t")
        output.append(str(round(float(old_steering_angle),2)) +"->")
        output.append(str(round(float(steering_angle),2)) +"\t" )
        output.append(str(round(float(throttle),2)) +"->" )
        output.append(str(round(float(new_throttle),2)) + "\n" )
        output_text = ''.join(output)
        myfile.write(output_text)
        #print(output_text)
        
        send_control(steering_angle, new_throttle)

# $ tail -f ~/dev/carnd/p3_behavioral_cloning/behavioral_cloning_UkiDLucas/output.txt 


# In[ ]:

if __name__ == '__main__':
    #parser = argparse.ArgumentParser(description='Remote Driving')
    #parser.add_argument('model', type=str,
    #help='Path to model definition h5. Model should be on the same path.')
    #args = parser.parse_args()

    #model = load_model(args.model)
    model = load_and_compile_model()
    
    
    # wrap Flask application with engineio's middleware
    app = socketio.Middleware(sio, app)

    # deploy as an eventlet WSGI server
    eventlet.wsgi.server(eventlet.listen(('', 4567)), app)

  parser = argparse.ArgumentParser(description='Remote Driving')
    parser.add_argument('model', type=str,
    help='Path to model definition json. Model weights should be on the same path.')
    args = parser.parse_args()
    with open(args.model, 'r') as jfile:
        model = model_from_json(jfile.read())


    model.compile("adam", "mse")
    weights_file = args.model.replace('json', 'h5')
    model.load_weights(weights_file)