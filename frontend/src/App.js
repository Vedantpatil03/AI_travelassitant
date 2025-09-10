import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import axios from 'axios';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Textarea } from './components/ui/textarea';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { 
  Send, 
  MapPin, 
  DollarSign, 
  Calendar, 
  Users, 
  Plane, 
  Camera,
  Sparkles,
  MessageCircle,
  Image as ImageIcon
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [sessionId] = useState(() => `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
  const [isLoading, setIsLoading] = useState(false);
  const [travelContext, setTravelContext] = useState({
    budget: '',
    location: '',
    duration: '',
    travelers: 1
  });
  const [generatedImage, setGeneratedImage] = useState(null);
  const [isGeneratingImage, setIsGeneratingImage] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Load chat history on component mount
    loadChatHistory();
  }, []);

  const loadChatHistory = async () => {
    try {
      const response = await axios.get(`${API}/chat-history/${sessionId}`);
      setMessages(response.data);
    } catch (error) {
      console.log('No previous chat history found');
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage = {
      id: Date.now().toString(),
      message: inputMessage,
      sender: 'user',
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await axios.post(`${API}/chat`, {
        message: inputMessage,
        session_id: sessionId,
        budget: travelContext.budget,
        location: travelContext.location,
        duration: travelContext.duration,
        travelers: travelContext.travelers
      });

      const aiMessage = {
        id: Date.now().toString() + '_ai',
        message: response.data.message,
        sender: 'assistant',
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, aiMessage]);
      setInputMessage('');
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        id: Date.now().toString() + '_error',
        message: 'Sorry, I encountered an error. Please try again.',
        sender: 'assistant',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const generateTripImage = async () => {
    if (!travelContext.location) {
      alert('Please specify a destination first!');
      return;
    }

    setIsGeneratingImage(true);
    try {
      const prompt = `${travelContext.location} travel destination, beautiful landscape, ${travelContext.budget ? `${travelContext.budget} style` : 'scenic view'}`;
      
      const response = await axios.post(`${API}/generate-trip-image`, {
        prompt: prompt,
        session_id: sessionId
      });

      setGeneratedImage(`data:image/png;base64,${response.data.image_base64}`);
    } catch (error) {
      console.error('Error generating image:', error);
      alert('Sorry, failed to generate trip image. Please try again.');
    } finally {
      setIsGeneratingImage(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const suggestedPrompts = [
    "Plan a 7-day trip to Japan for 2 people",
    "Find budget-friendly destinations in Europe",
    "Suggest a romantic getaway for our anniversary",
    "Plan a family vacation with kids",
    "What are the best adventure destinations?"
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-amber-50 to-yellow-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-orange-100 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-gradient-to-r from-orange-500 to-amber-500 rounded-xl">
                <Plane className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-orange-600 to-amber-600 bg-clip-text text-transparent">
                  TravelBot AI
                </h1>
                <p className="text-sm text-orange-600">Your Personal Travel Assistant</p>
              </div>
            </div>
            <Badge variant="secondary" className="bg-orange-100 text-orange-700">
              <Sparkles className="h-3 w-3 mr-1" />
              Powered by GPT-5
            </Badge>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Travel Context Panel */}
          <div className="lg:col-span-1">
            <Card className="bg-white/70 backdrop-blur-sm border-orange-200 shadow-lg">
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center text-orange-800">
                  <MapPin className="h-5 w-5 mr-2" />
                  Trip Details
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-orange-700 mb-2 block">
                    <MapPin className="h-4 w-4 inline mr-1" />
                    Destination
                  </label>
                  <Input
                    placeholder="e.g., Tokyo, Japan"
                    value={travelContext.location}
                    onChange={(e) => setTravelContext(prev => ({...prev, location: e.target.value}))}
                    className="border-orange-200 focus:border-orange-400"
                  />
                </div>
                
                <div>
                  <label className="text-sm font-medium text-orange-700 mb-2 block">
                    <DollarSign className="h-4 w-4 inline mr-1" />
                    Budget Range
                  </label>
                  <Input
                    placeholder="e.g., $2000-3000"
                    value={travelContext.budget}
                    onChange={(e) => setTravelContext(prev => ({...prev, budget: e.target.value}))}
                    className="border-orange-200 focus:border-orange-400"
                  />
                </div>
                
                <div>
                  <label className="text-sm font-medium text-orange-700 mb-2 block">
                    <Calendar className="h-4 w-4 inline mr-1" />
                    Duration
                  </label>
                  <Input
                    placeholder="e.g., 7 days"
                    value={travelContext.duration}
                    onChange={(e) => setTravelContext(prev => ({...prev, duration: e.target.value}))}
                    className="border-orange-200 focus:border-orange-400"
                  />
                </div>
                
                <div>
                  <label className="text-sm font-medium text-orange-700 mb-2 block">
                    <Users className="h-4 w-4 inline mr-1" />
                    Travelers
                  </label>
                  <Input
                    type="number"
                    min="1"
                    value={travelContext.travelers}
                    onChange={(e) => setTravelContext(prev => ({...prev, travelers: parseInt(e.target.value) || 1}))}
                    className="border-orange-200 focus:border-orange-400"
                  />
                </div>

                <Button 
                  onClick={generateTripImage}
                  disabled={isGeneratingImage || !travelContext.location}
                  className="w-full bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white"
                >
                  {isGeneratingImage ? (
                    <>
                      <Sparkles className="h-4 w-4 mr-2 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <ImageIcon className="h-4 w-4 mr-2" />
                      Generate Trip Visual
                    </>
                  )}
                </Button>

                {generatedImage && (
                  <div className="mt-4">
                    <img 
                      src={generatedImage} 
                      alt="Generated trip visual" 
                      className="w-full rounded-lg shadow-md"
                    />
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Chat Interface */}
          <div className="lg:col-span-3">
            <Card className="bg-white/70 backdrop-blur-sm border-orange-200 shadow-lg h-[700px] flex flex-col">
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center text-orange-800">
                  <MessageCircle className="h-5 w-5 mr-2" />
                  Travel Assistant Chat
                </CardTitle>
              </CardHeader>
              
              <CardContent className="flex-1 flex flex-col p-0">
                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4">
                  {messages.length === 0 && (
                    <div className="text-center py-12">
                      <div className="mb-6">
                        <div className="w-20 h-20 mx-auto bg-gradient-to-r from-orange-500 to-amber-500 rounded-full flex items-center justify-center mb-4">
                          <Camera className="h-10 w-10 text-white" />
                        </div>
                        <h3 className="text-xl font-semibold text-orange-800 mb-2">
                          Welcome to TravelBot AI!
                        </h3>
                        <p className="text-orange-600 max-w-md mx-auto">
                          I'm here to help you plan amazing trips. Tell me about your dream destination or ask for travel advice!
                        </p>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl mx-auto">
                        {suggestedPrompts.map((prompt, index) => (
                          <Button
                            key={index}
                            variant="outline"
                            className="text-left h-auto p-3 text-orange-700 border-orange-200 hover:bg-orange-50"
                            onClick={() => setInputMessage(prompt)}
                          >
                            {prompt}
                          </Button>
                        ))}
                      </div>
                    </div>
                  )}

                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[80%] p-4 rounded-2xl ${
                          message.sender === 'user'
                            ? 'bg-gradient-to-r from-orange-500 to-amber-500 text-white ml-4'
                            : 'bg-white border border-orange-200 text-gray-800 mr-4'
                        }`}
                      >
                        <div className="whitespace-pre-wrap">{message.message}</div>
                        <div
                          className={`text-xs mt-2 ${
                            message.sender === 'user' ? 'text-orange-100' : 'text-gray-500'
                          }`}
                        >
                          {new Date(message.timestamp).toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                  ))}

                  {isLoading && (
                    <div className="flex justify-start">
                      <div className="bg-white border border-orange-200 text-gray-800 p-4 rounded-2xl mr-4">
                        <div className="flex items-center space-x-2">
                          <div className="flex space-x-1">
                            <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce"></div>
                            <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                            <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                          </div>
                          <span className="text-sm text-orange-600">TravelBot is thinking...</span>
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div className="border-t border-orange-200 p-6">
                  <div className="flex space-x-3">
                    <Textarea
                      value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder="Ask me about travel plans, destinations, budgets, or anything travel-related..."
                      className="flex-1 min-h-[50px] border-orange-200 focus:border-orange-400 resize-none"
                    />
                    <Button
                      onClick={sendMessage}
                      disabled={isLoading || !inputMessage.trim()}
                      className="bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white px-6"
                    >
                      <Send className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-white/70 backdrop-blur-sm border-t border-orange-100 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center text-orange-600">
            <p className="text-sm">
              © 2025 TravelBot AI - Your intelligent travel companion powered by advanced AI
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;