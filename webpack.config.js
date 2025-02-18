const path = require("path");

module.exports = {
  entry: "./frontend/index.ts", // path to our input file
  output: {
    filename: "index-bundle.js", // output bundle file name
    path: path.resolve(__dirname, "./static"), // path to our Django static directory
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        loader: "babel-loader",
        options: { presets: ["@babel/preset-env", "@babel/preset-react"] },
      },
      {
        test: /\.tsx?$/,
        use: "ts-loader",
        exclude: /node_modules/,
      },
    ],
  },
  resolve: {
    extensions: [".tsx", ".ts", ".js"],
  },
};