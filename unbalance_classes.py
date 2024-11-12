import torch
from transformers import BertTokenizer, BertForSequenceClassification, Trainer, TrainingArguments
from datasets import Dataset
from sklearn.utils.class_weight import compute_class_weight

# Загрузка токенизатора и модели BERT
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertForSequenceClassification.from_pretrained('bert-base-uncased', num_labels=2)

# Пример данных
data = {
    "text": ["пример текста 1", "пример текста 2", ...],
    "label": [0, 1, ...]
}

# Создание Dataset объекта
dataset = Dataset.from_dict(data)

# Функция токенизации
def tokenize_function(examples):
    return tokenizer(examples['text'], padding='max_length', truncation=True)

# Применение токенизации
tokenized_datasets = dataset.map(tokenize_function, batched=True)

# Вычисление весов классов
class_weights = compute_class_weight('balanced', classes=[0, 1], y=data["label"])
class_weights_tensor = torch.tensor(class_weights, dtype=torch.float)

# Custom Trainer для взвешивания классов
class WeightedTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False):
        labels = inputs.get("labels")
        outputs = model(**inputs)
        logits = outputs.get("logits")
        
        # Использование взвешенной потери
        loss_fct = torch.nn.CrossEntropyLoss(weight=class_weights_tensor)
        loss = loss_fct(logits.view(-1, self.model.config.num_labels), labels.view(-1))
        
        return (loss, outputs) if return_outputs else loss

# Параметры обучения
training_args = TrainingArguments(
    output_dir="./results",
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    num_train_epochs=3,
    weight_decay=0.01,
    logging_dir='./logs'
)

# Создание тренера
trainer = WeightedTrainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets,
)

# Запуск обучения
trainer.train()
